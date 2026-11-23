from fastapi.testclient import TestClient

from taskhub.core.enums import ProjectStatus
from taskhub.main import app


def test_create_project_in_workspace(
    client: TestClient,
    editor_headers: dict[str, str],
    viewer_headers: dict[str, str],
    stranger_headers: dict[str, str],
):
    # 1. OWNER can create project in workspace (201)
    payload_owner = {
        "name": "Owner Project",
        "description": "Project created by owner",
    }
    resp_owner = client.post("/api/v1/workspaces/1/projects", json=payload_owner)
    assert resp_owner.status_code == 201
    data_owner = resp_owner.json()
    assert data_owner["name"] == "Owner Project"
    assert data_owner["description"] == "Project created by owner"
    assert data_owner["workspace_id"] == 1
    assert data_owner["owner_id"] == 1
    assert data_owner["status"] == ProjectStatus.ACTIVE.value
    assert "id" in data_owner
    assert "created_at" in data_owner

    # 2. EDITOR can create project in workspace (201)
    with TestClient(app, headers=editor_headers) as editor_client:
        payload_editor = {
            "name": "Editor Project",
            "description": "Project created by editor",
        }
        resp_editor = editor_client.post("/api/v1/workspaces/1/projects", json=payload_editor)
        assert resp_editor.status_code == 201
        data_editor = resp_editor.json()
        assert data_editor["name"] == "Editor Project"
        assert data_editor["workspace_id"] == 1
        assert data_editor["owner_id"] == 5
        assert data_editor["status"] == ProjectStatus.ACTIVE.value

    # 3. VIEWER cannot create project in workspace (403)
    with TestClient(app, headers=viewer_headers) as viewer_client:
        payload_viewer = {
            "name": "Viewer Project",
            "description": "Should fail",
        }
        resp_viewer = viewer_client.post("/api/v1/workspaces/1/projects", json=payload_viewer)
        assert resp_viewer.status_code == 403
        assert "Only workspace OWNER" in resp_viewer.json()["detail"]

    # 4. Stranger cannot create project in workspace (403)
    with TestClient(app, headers=stranger_headers) as stranger_client:
        payload_stranger = {
            "name": "Stranger Project",
            "description": "Should fail",
        }
        resp_stranger = stranger_client.post("/api/v1/workspaces/1/projects", json=payload_stranger)
        assert resp_stranger.status_code == 403
        assert "Not a member" in resp_stranger.json()["detail"]


def test_list_workspace_projects_pagination(
    client: TestClient,
    editor_headers: dict[str, str],
    viewer_headers: dict[str, str],
    stranger_headers: dict[str, str],
):
    # Member (VIEWER) can list projects with pagination and X-Total-Count header
    with TestClient(app, headers=viewer_headers) as viewer_client:
        resp = viewer_client.get("/api/v1/workspaces/1/projects?page=1&limit=2")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 2
        assert "X-Total-Count" in resp.headers
        total = int(resp.headers["X-Total-Count"])
        assert total >= 3

        # Page 2
        resp_page2 = viewer_client.get("/api/v1/workspaces/1/projects?page=2&limit=2")
        assert resp_page2.status_code == 200
        data_page2 = resp_page2.json()
        assert len(data_page2) >= 1

    # Member (EDITOR) can list projects
    with TestClient(app, headers=editor_headers) as editor_client:
        resp_editor = editor_client.get("/api/v1/workspaces/1/projects")
        assert resp_editor.status_code == 200
        assert "X-Total-Count" in resp_editor.headers

    # Stranger cannot list projects (403)
    with TestClient(app, headers=stranger_headers) as stranger_client:
        resp_stranger = stranger_client.get("/api/v1/workspaces/1/projects")
        assert resp_stranger.status_code == 403
        assert "Not a member" in resp_stranger.json()["detail"]


def test_update_and_archive_project(
    client: TestClient,
    editor_headers: dict[str, str],
    viewer_headers: dict[str, str],
    stranger_headers: dict[str, str],
):
    # 1. EDITOR can update and archive project (200)
    with TestClient(app, headers=editor_headers) as editor_client:
        resp_archive = editor_client.patch(
            "/api/v1/projects/1",
            json={"status": ProjectStatus.ARCHIVED.value, "name": "Project Alpha Archived"},
        )
        assert resp_archive.status_code == 200
        data_archived = resp_archive.json()
        assert data_archived["status"] == ProjectStatus.ARCHIVED.value
        assert data_archived["name"] == "Project Alpha Archived"

    # Verify project is indeed archived via GET
    resp_get = client.get("/api/v1/projects/1")
    assert resp_get.status_code == 200
    assert resp_get.json()["status"] == ProjectStatus.ARCHIVED.value

    # 2. VIEWER cannot update project (403)
    with TestClient(app, headers=viewer_headers) as viewer_client:
        resp_viewer = viewer_client.patch("/api/v1/projects/1", json={"name": "Viewer Try Update"})
        assert resp_viewer.status_code == 403

    # 3. Stranger cannot update project (403)
    with TestClient(app, headers=stranger_headers) as stranger_client:
        resp_stranger = stranger_client.patch(
            "/api/v1/projects/1",
            json={"name": "Stranger Try Update"},
        )
        assert resp_stranger.status_code == 403

    # 4. While ARCHIVED, modifying name/description is BLOCKED -> 400
    with TestClient(app, headers=editor_headers) as editor_client:
        resp_blocked = editor_client.patch(
            "/api/v1/projects/1",
            json={"name": "Rename While Archived"},
        )
        assert resp_blocked.status_code == 400
        assert "Cannot modify an archived project" in resp_blocked.json()["detail"]

        # 5. Un-archive project back to ACTIVE -> 200
        resp_unarchive = editor_client.patch(
            "/api/v1/projects/1",
            json={"status": ProjectStatus.ACTIVE.value},
        )
        assert resp_unarchive.status_code == 200
        assert resp_unarchive.json()["status"] == ProjectStatus.ACTIVE.value

        # 6. Now that it is ACTIVE, editing name works again -> 200
        resp_active_update = editor_client.patch(
            "/api/v1/projects/1",
            json={"name": "Project Alpha Active Again"},
        )
        assert resp_active_update.status_code == 200
        assert resp_active_update.json()["name"] == "Project Alpha Active Again"


def test_list_workspace_projects_hides_archived_by_default(
    client: TestClient,
    editor_headers: dict[str, str],
):
    with TestClient(app, headers=editor_headers) as editor_client:
        # Create a new project to archive
        resp_create = editor_client.post(
            "/api/v1/workspaces/1/projects",
            json={"name": "Project To Archive", "description": "Temp"},
        )
        assert resp_create.status_code == 201
        temp_proj_id = resp_create.json()["id"]

        # Default list includes this newly created project
        resp_list1 = editor_client.get("/api/v1/workspaces/1/projects")
        assert resp_list1.status_code == 200
        total_before = int(resp_list1.headers["X-Total-Count"])
        ids_before = [p["id"] for p in resp_list1.json()]
        assert temp_proj_id in ids_before

        # Archive the project
        resp_archive = editor_client.patch(
            f"/api/v1/projects/{temp_proj_id}",
            json={"status": ProjectStatus.ARCHIVED.value},
        )
        assert resp_archive.status_code == 200

        # Default list (include_archived=False) MUST hide the archived project
        resp_list2 = editor_client.get("/api/v1/workspaces/1/projects")
        assert resp_list2.status_code == 200
        total_after = int(resp_list2.headers["X-Total-Count"])
        assert total_after == total_before - 1
        ids_after = [p["id"] for p in resp_list2.json()]
        assert temp_proj_id not in ids_after

        # Explicit include_archived=true MUST return the archived project
        resp_list_all = editor_client.get(
            "/api/v1/workspaces/1/projects?include_archived=true"
        )
        assert resp_list_all.status_code == 200
        total_all = int(resp_list_all.headers["X-Total-Count"])
        assert total_all == total_before
        ids_all = [p["id"] for p in resp_list_all.json()]
        assert temp_proj_id in ids_all


def test_delete_project_owner_only(
    client: TestClient,
    editor_headers: dict[str, str],
    viewer_headers: dict[str, str],
    stranger_headers: dict[str, str],
):
    # 1. VIEWER cannot delete project (403)
    with TestClient(app, headers=viewer_headers) as viewer_client:
        resp_viewer = viewer_client.delete("/api/v1/projects/1")
        assert resp_viewer.status_code == 403

    # 2. EDITOR cannot delete project (403)
    with TestClient(app, headers=editor_headers) as editor_client:
        resp_editor = editor_client.delete("/api/v1/projects/1")
        assert resp_editor.status_code == 403

    # 3. Stranger cannot delete project (403)
    with TestClient(app, headers=stranger_headers) as stranger_client:
        resp_stranger = stranger_client.delete("/api/v1/projects/1")
        assert resp_stranger.status_code == 403

    # 4. OWNER deletes project successfully (204)
    resp_owner = client.delete("/api/v1/projects/1")
    assert resp_owner.status_code == 204

    # Verify project is deleted (404)
    resp_check = client.get("/api/v1/projects/1")
    assert resp_check.status_code == 404
