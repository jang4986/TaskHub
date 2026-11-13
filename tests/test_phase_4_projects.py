from fastapi.testclient import TestClient

from taskhub.main import app


def test_owner_can_create_project_in_workspace(client: TestClient):
    payload = {
        "name": "New Web App",
        "description": "Backend API project",
    }
    response = client.post("/api/v1/workspaces/1/projects", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "New Web App"
    assert data["description"] == "Backend API project"
    assert data["workspace_id"] == 1
    assert data["owner_id"] == 1
    assert "id" in data
    assert "created_at" in data


def test_member_cannot_create_project(user2_headers: dict[str, str]):
    with TestClient(app, headers=user2_headers) as user2_client:
        payload = {
            "name": "Unauthorized Project",
            "description": "Should fail",
        }
        response = user2_client.post("/api/v1/workspaces/1/projects", json=payload)
        assert response.status_code == 403
        assert "Only workspace OWNER or ADMIN" in response.json()["detail"]


def test_stranger_cannot_create_project(stranger_headers: dict[str, str]):
    with TestClient(app, headers=stranger_headers) as stranger_client:
        payload = {
            "name": "Stranger Project",
            "description": "Should fail",
        }
        response = stranger_client.post("/api/v1/workspaces/1/projects", json=payload)
        assert response.status_code == 403
        assert "Not a member" in response.json()["detail"]


def test_list_workspace_projects(
    client: TestClient,
    user2_headers: dict[str, str],
    stranger_headers: dict[str, str],
):
    # Member (User 2) can list projects of workspace 1
    with TestClient(app, headers=user2_headers) as user2_client:
        response = user2_client.get("/api/v1/workspaces/1/projects")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 3
        assert "X-Total-Count" in response.headers
        assert int(response.headers["X-Total-Count"]) >= 3

    # Stranger (User 4) cannot list projects
    with TestClient(app, headers=stranger_headers) as stranger_client:
        resp_stranger = stranger_client.get("/api/v1/workspaces/1/projects")
        assert resp_stranger.status_code == 403
        assert "Not a member" in resp_stranger.json()["detail"]


def test_get_project_detail_and_forbidden(
    client: TestClient,
    user2_headers: dict[str, str],
    stranger_headers: dict[str, str],
):
    # Member (User 2) can view project details
    with TestClient(app, headers=user2_headers) as user2_client:
        resp = user2_client.get("/api/v1/projects/1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == 1
        assert data["name"] == "Project Alpha"
        assert data["workspace_id"] == 1

    # Stranger cannot view project details
    with TestClient(app, headers=stranger_headers) as stranger_client:
        resp_stranger = stranger_client.get("/api/v1/projects/1")
        assert resp_stranger.status_code == 403
        assert "Not a member" in resp_stranger.json()["detail"]

    # Non-existent project returns 404
    resp_404 = client.get("/api/v1/projects/99999")
    assert resp_404.status_code == 404
    assert "Project not found" in resp_404.json()["detail"]


def test_delete_project_permissions(client: TestClient, user2_headers: dict[str, str]):
    # Member (User 2) cannot delete project
    with TestClient(app, headers=user2_headers) as user2_client:
        resp_forbidden = user2_client.delete("/api/v1/projects/1")
        assert resp_forbidden.status_code == 403
        assert "Only workspace OWNER or ADMIN" in resp_forbidden.json()["detail"]

    # Owner (User 1) can delete project
    resp_success = client.delete("/api/v1/projects/1")
    assert resp_success.status_code == 204

    # Verify project is deleted
    resp_check = client.get("/api/v1/projects/1")
    assert resp_check.status_code == 404
