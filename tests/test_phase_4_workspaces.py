from fastapi.testclient import TestClient

from taskhub.core.enums import WorkspaceRole


def test_create_workspace_success(client: TestClient):
    payload = {
        "name": "Acme Workspace",
        "description": "Acme organization workspace",
    }
    response = client.post("/api/v1/workspaces", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Acme Workspace"
    assert data["slug"] == "acme-workspace"
    assert data["owner_id"] == 1
    assert "id" in data
    assert "created_at" in data

    # Verify workspace detail includes owner as member with role OWNER
    ws_id = data["id"]
    detail_res = client.get(f"/api/v1/workspaces/{ws_id}")
    assert detail_res.status_code == 200
    detail_data = detail_res.json()
    assert len(detail_data["members"]) >= 1
    owner_member = next(
        (m for m in detail_data["members"] if m["user_id"] == 1),
        None,
    )
    assert owner_member is not None
    assert owner_member["role"] == WorkspaceRole.OWNER.value
    assert "joined_at" in owner_member


def test_list_my_workspaces(client: TestClient, stranger_headers: dict[str, str]):
    # User 1 is owner of Workspace Alpha (id=1)
    res_user1 = client.get("/api/v1/workspaces")
    assert res_user1.status_code == 200
    data_user1 = res_user1.json()
    assert any(ws["id"] == 1 for ws in data_user1)
    assert "X-Total-Count" in res_user1.headers
    assert int(res_user1.headers["X-Total-Count"]) >= 1

    # Stranger (User 4) is neither owner nor member of any workspace initially
    from taskhub.main import app
    with TestClient(app, headers=stranger_headers) as stranger_client:
        res_stranger = stranger_client.get("/api/v1/workspaces")
        assert res_stranger.status_code == 200
        data_stranger = res_stranger.json()
        assert len(data_stranger) == 0
        assert res_stranger.headers["X-Total-Count"] == "0"


def test_get_workspace_detail_forbidden_for_non_member(stranger_headers: dict[str, str]):
    from taskhub.main import app
    with TestClient(app, headers=stranger_headers) as stranger_client:
        res = stranger_client.get("/api/v1/workspaces/1")
        assert res.status_code == 403
        assert "Not a member" in res.json()["detail"]


def test_add_member_success(client: TestClient):
    payload = {
        "email": "stranger@example.com",
        "role": WorkspaceRole.MEMBER.value,
    }
    response = client.post("/api/v1/workspaces/1/members", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["workspace_id"] == 1
    assert data["user_id"] == 4
    assert data["role"] == WorkspaceRole.MEMBER.value
    assert "joined_at" in data
    assert data["user"] is not None
    assert data["user"]["email"] == "stranger@example.com"


def test_add_member_duplicate_conflict(client: TestClient):
    # User 2 is already a member of workspace 1 (from conftest.py)
    payload = {
        "email": "user2@example.com",
        "role": WorkspaceRole.MEMBER.value,
    }
    response = client.post("/api/v1/workspaces/1/members", json=payload)
    assert response.status_code == 409
    assert "already a member" in response.json()["detail"]


def test_add_member_nonexistent_email(client: TestClient):
    payload = {
        "email": "notfound_user@example.com",
        "role": WorkspaceRole.MEMBER.value,
    }
    response = client.post("/api/v1/workspaces/1/members", json=payload)
    assert response.status_code == 404
    assert "User with this email not found" in response.json()["detail"]


def test_add_member_owner_role_forbidden_422(client: TestClient):
    # Inviting someone with role OWNER must be rejected with 422 Unprocessable Entity
    payload = {
        "email": "stranger@example.com",
        "role": "OWNER",
    }
    response = client.post("/api/v1/workspaces/1/members", json=payload)
    assert response.status_code == 422


def test_remove_member_owner_protection(client: TestClient):
    # User 1 is the owner of workspace 1
    response = client.delete("/api/v1/workspaces/1/members/1")
    assert response.status_code == 400
    assert "Cannot remove the workspace owner" in response.json()["detail"]


def test_delete_workspace_permission(client: TestClient, viewer_headers: dict[str, str]):
    from taskhub.main import app
    # Viewer (User 3) is a member, not owner of workspace 1
    with TestClient(app, headers=viewer_headers) as viewer_client:
        res_forbidden = viewer_client.delete("/api/v1/workspaces/1")
        assert res_forbidden.status_code == 403
        assert "Only the workspace owner" in res_forbidden.json()["detail"]

    # Owner (User 1) deletes workspace 1
    res_success = client.delete("/api/v1/workspaces/1")
    assert res_success.status_code == 204

    # Workspace 1 should no longer exist
    res_check = client.get("/api/v1/workspaces/1")
    assert res_check.status_code == 404
