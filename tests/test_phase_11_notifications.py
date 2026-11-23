from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from taskhub.db.session import AsyncSessionLocal
from taskhub.main import app
from taskhub.services.notification_service import set_notification_session_factory
from tests.conftest import TestingSessionLocal


@pytest.fixture(autouse=True)
def configure_test_session_factory() -> Generator[None, None, None]:
    """Ensure background tasks run against the in-memory test database."""
    set_notification_session_factory(TestingSessionLocal)
    yield
    set_notification_session_factory(AsyncSessionLocal)


def test_background_notification_on_create_task_with_assignee(
    client: TestClient,
    user2_headers: dict[str, str],
):
    """Creating a task with assignee triggers background notification to that assignee."""
    project_id = 1
    assignee_id = 2  # User 2 is a member of workspace 1

    # 1. User 1 (client) creates a task assigned to User 2
    resp_create = client.post(
        f"/api/v1/projects/{project_id}/tasks",
        json={
            "title": "Notification Background Test Task",
            "assignee_id": assignee_id,
        },
    )
    assert resp_create.status_code == 201
    assert "id" in resp_create.json()

    # 2. User 2 logs in and checks notifications
    with TestClient(app, headers=user2_headers) as u2_client:
        resp_notif = u2_client.get("/api/v1/notifications")
        assert resp_notif.status_code == 200
        assert "X-Total-Count" in resp_notif.headers
        assert int(resp_notif.headers["X-Total-Count"]) >= 1

        notifs = resp_notif.json()
        assert isinstance(notifs, list)
        matching = [
            n for n in notifs if "Notification Background Test Task" in n["message"]
        ]
        assert len(matching) >= 1
        notif = matching[0]
        assert notif["user_id"] == assignee_id
        assert notif["type"] == "TASK_ASSIGNED"
        assert notif["title"] == "New Task Assigned"
        assert "Notification Background Test Task" in notif["message"]
        assert notif["is_read"] is False


def test_background_notification_on_reassign_task(
    client: TestClient,
    user2_headers: dict[str, str],
):
    """Reassigning task notifies new user; updating without reassigning does not."""
    project_id = 1

    # 1. Create a task without an assignee (assignee_id is None)
    resp_create = client.post(
        f"/api/v1/projects/{project_id}/tasks",
        json={"title": "Unassigned Task"},
    )
    assert resp_create.status_code == 201
    task_id = resp_create.json()["id"]

    # 2. Check User 2 initial notification count
    with TestClient(app, headers=user2_headers) as u2_client:
        resp_init = u2_client.get("/api/v1/notifications")
        assert resp_init.status_code == 200
        count_before = int(resp_init.headers["X-Total-Count"])

    # 3. Patch task to assign to User 2 -> Triggers notification
    resp_patch = client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"assignee_id": 2},
    )
    assert resp_patch.status_code == 200
    assert resp_patch.json()["assignee_id"] == 2

    with TestClient(app, headers=user2_headers) as u2_client:
        resp_after = u2_client.get("/api/v1/notifications")
        assert resp_after.status_code == 200
        count_after = int(resp_after.headers["X-Total-Count"])
        assert count_after == count_before + 1

    # 4. Patch task updating only title (assignee remains 2) -> NO duplicate notification
    resp_patch2 = client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"title": "Updated Title Same Assignee"},
    )
    assert resp_patch2.status_code == 200

    with TestClient(app, headers=user2_headers) as u2_client:
        resp_after2 = u2_client.get("/api/v1/notifications")
        assert resp_after2.status_code == 200
        count_after2 = int(resp_after2.headers["X-Total-Count"])
        assert count_after2 == count_after


def test_mark_notification_as_read_and_authorization(
    client: TestClient,
    user2_headers: dict[str, str],
):
    """Users can mark their own notifications as read; modifying another's is forbidden."""
    project_id = 1

    # 1. Create a task assigned to User 2 to generate a notification
    resp_create = client.post(
        f"/api/v1/projects/{project_id}/tasks",
        json={"title": "Task for Read Test", "assignee_id": 2},
    )
    assert resp_create.status_code == 201

    with TestClient(app, headers=user2_headers) as u2_client:
        resp_notif = u2_client.get("/api/v1/notifications?unread_only=true")
        assert resp_notif.status_code == 200
        notifs = resp_notif.json()
        assert len(notifs) >= 1
        notif_id = notifs[0]["id"]
        assert notifs[0]["is_read"] is False

    # 2. User 1 (client) attempts to mark User 2's notification as read -> 403 Forbidden
    resp_forbidden = client.patch(f"/api/v1/notifications/{notif_id}/read")
    assert resp_forbidden.status_code == 403
    assert "cannot modify notifications" in resp_forbidden.json()["detail"].lower()

    # 3. User 2 marks their own notification as read -> 200 OK, is_read = True
    with TestClient(app, headers=user2_headers) as u2_client:
        resp_read = u2_client.patch(f"/api/v1/notifications/{notif_id}/read")
        assert resp_read.status_code == 200
        data = resp_read.json()
        assert data["id"] == notif_id
        assert data["is_read"] is True

        # Check with unread_only=true -> This notification should no longer appear
        resp_unread = u2_client.get("/api/v1/notifications?unread_only=true")
        assert resp_unread.status_code == 200
        unread_ids = [n["id"] for n in resp_unread.json()]
        assert notif_id not in unread_ids

    # 4. Attempt to mark nonexistent notification -> 404 Not Found
    with TestClient(app, headers=user2_headers) as u2_client:
        resp_404 = u2_client.patch("/api/v1/notifications/99999/read")
        assert resp_404.status_code == 404
