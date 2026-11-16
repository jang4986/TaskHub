from fastapi.testclient import TestClient

from taskhub.core.enums import UserRole
from taskhub.core.security import decode_access_token


def test_register_success(unauth_client: TestClient):
    """Test user registration successfully hashes password in DB and defaults to MEMBER role."""
    payload = {
        "email": "newuser@example.com",
        "full_name": "New User",
        "password": "securepassword123",
    }
    response = unauth_client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert data["email"] == payload["email"]
    assert data["full_name"] == payload["full_name"]
    assert data["role"] == UserRole.MEMBER.value
    assert "id" in data
    assert "hashed_password" not in data


def test_register_duplicate_email(unauth_client: TestClient):
    """Test registration fails with 409 Conflict when email already exists."""
    payload = {
        "email": "user1@example.com",  # Already seeded in conftest
        "full_name": "Duplicate User",
        "password": "somepassword123",
    }
    response = unauth_client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 409
    assert response.json()["detail"] == "Email already registered"


def test_login_success(unauth_client: TestClient):
    """Test login via OAuth2 form returns JWT token with sub, role, type, jti, iat claims."""
    form_payload = {
        "username": "user1@example.com",
        "password": "password123",
    }
    response = unauth_client.post("/api/v1/auth/login", data=form_payload)
    assert response.status_code == 200

    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

    # Verify decoded token claims
    payload = decode_access_token(data["access_token"])
    assert payload is not None
    assert payload["sub"] == "1"
    assert payload["role"] == UserRole.MEMBER.value
    assert payload["type"] == "access"
    assert "jti" in payload
    assert "iat" in payload


def test_login_wrong_password(unauth_client: TestClient):
    """Test login with incorrect password returns 401 Unauthorized."""
    payload = {
        "username": "user1@example.com",
        "password": "wrongpassword",
    }
    response = unauth_client.post("/api/v1/auth/login", data=payload)
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"


def test_login_nonexistent_user(unauth_client: TestClient):
    """Test login with nonexistent email runs dummy hash and returns 401 Unauthorized."""
    payload = {
        "username": "nonexistent@example.com",
        "password": "password123",
    }
    response = unauth_client.post("/api/v1/auth/login", data=payload)
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"


def test_login_inactive_user(unauth_client: TestClient):
    """Test login with inactive user returns 403 Forbidden."""
    payload = {
        "username": "inactive@example.com",
        "password": "password123",
    }
    response = unauth_client.post("/api/v1/auth/login", data=payload)
    assert response.status_code == 403
    assert response.json()["detail"] == "Inactive user"


def test_get_me(client: TestClient, unauth_client: TestClient):
    """Test GET /api/v1/auth/me returns current user info when authenticated."""
    # 1. Unauthenticated request -> 401
    resp_unauth = unauth_client.get("/api/v1/auth/me")
    assert resp_unauth.status_code == 401

    # 2. Authenticated request -> 200
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert data["email"] == "user1@example.com"
    assert data["role"] == UserRole.MEMBER.value


def test_access_task_without_auth(unauth_client: TestClient):
    """Test calling task API without token returns 401 Unauthorized."""
    task_payload = {
        "title": "Task without token",
        "description": "Should fail with 401",
    }
    response = unauth_client.post("/api/v1/projects/1/tasks", json=task_payload)
    assert response.status_code == 401


def test_rbac_admin_endpoint(
    unauth_client: TestClient,
    member_headers: dict[str, str],
    admin_headers: dict[str, str],
):
    """Test RBAC: MEMBER gets 403 Forbidden on Admin endpoint,
    ADMIN gets 200 OK with total header.
    """
    # 1. Without auth -> 401
    resp_unauth = unauth_client.get("/api/v1/users")
    assert resp_unauth.status_code == 401

    # 2. As MEMBER -> 403 Forbidden
    resp_member = unauth_client.get("/api/v1/users", headers=member_headers)
    assert resp_member.status_code == 403
    assert resp_member.json()["detail"] == "The user doesn't have enough privileges"

    # 3. As ADMIN -> 200 OK
    resp_admin = unauth_client.get("/api/v1/users", headers=admin_headers)
    assert resp_admin.status_code == 200
    assert "X-Total-Count" in resp_admin.headers
    users_list = resp_admin.json()
    assert isinstance(users_list, list)
    assert len(users_list) >= 2


def test_project_access_control(
    unauth_client: TestClient,
    stranger_headers: dict[str, str],
    viewer_headers: dict[str, str],
    member_headers: dict[str, str],
):
    """Test project isolation and role permissions for task manipulation."""
    task_payload = {
        "title": "Permission test task",
        "description": "Validating RBAC on project tasks",
    }

    # 1. Stranger user (not in workspace/project) cannot access or create tasks -> 403 Forbidden
    resp_stranger = unauth_client.post(
        "/api/v1/projects/1/tasks",
        json=task_payload,
        headers=stranger_headers,
    )
    assert resp_stranger.status_code == 403

    # 2. Viewer in workspace cannot create task -> 403 Forbidden
    resp_viewer = unauth_client.post(
        "/api/v1/projects/1/tasks",
        json=task_payload,
        headers=viewer_headers,
    )
    assert resp_viewer.status_code == 403

    # 3. Project owner can create task -> 201 Created
    resp_owner = unauth_client.post(
        "/api/v1/projects/1/tasks",
        json=task_payload,
        headers=member_headers,
    )
    assert resp_owner.status_code == 201
    created_id = resp_owner.json()["id"]

    # 4. Viewer CAN read tasks -> 200 OK
    resp_viewer_get = unauth_client.get(
        f"/api/v1/tasks/{created_id}",
        headers=viewer_headers,
    )
    assert resp_viewer_get.status_code == 200

    # 5. Viewer CANNOT delete task -> 403 Forbidden
    resp_viewer_del = unauth_client.delete(
        f"/api/v1/tasks/{created_id}",
        headers=viewer_headers,
    )
    assert resp_viewer_del.status_code == 403


def test_update_not_null_field_with_null(client: TestClient):
    """Test sending 'title': None raises 422 Unprocessable Entity instead of 500 DB error."""
    # Create task
    task = client.post(
        "/api/v1/projects/1/tasks",
        json={"title": "Original task title"},
    ).json()
    task_id = task["id"]

    # Patch with null title
    response = client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"title": None},
    )
    assert response.status_code == 422
    assert "cannot be null" in response.json()["detail"]
