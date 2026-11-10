from fastapi.testclient import TestClient

from taskhub.core.security import verify_password
from taskhub.enums.common import UserRole
from tests.conftest import TestingSessionLocal
from taskhub.models.user import User
from sqlalchemy import select


def test_register_success(unauth_client: TestClient):
    """Test user registration successfully hashes password in DB."""
    payload = {
        "email": "newuser@example.com",
        "full_name": "New User",
        "password": "securepassword123",
        "role": "MEMBER",
    }
    response = unauth_client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert data["email"] == payload["email"]
    assert data["full_name"] == payload["full_name"]
    assert data["role"] == "MEMBER"
    assert "id" in data
    assert "hashed_password" not in data


def test_register_duplicate_email(unauth_client: TestClient):
    """Test registration fails with 400 when email already exists."""
    payload = {
        "email": "user1@example.com",  # Already seeded in conftest
        "full_name": "Duplicate User",
        "password": "somepassword123",
    }
    response = unauth_client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 400
    assert response.json()["detail"] == "Email already registered"


def test_login_success(unauth_client: TestClient):
    """Test login returns JWT token with bearer type for JSON and form."""
    # 1. Login with JSON payload
    json_payload = {
        "email": "user1@example.com",
        "password": "password123",
    }
    resp_json = unauth_client.post("/api/v1/auth/login", json=json_payload)
    assert resp_json.status_code == 200
    data_json = resp_json.json()
    assert "access_token" in data_json
    assert data_json["token_type"] == "bearer"

    # 2. Login with form payload (OAuth2 standard)
    form_payload = {
        "username": "user1@example.com",
        "password": "password123",
    }
    resp_form = unauth_client.post("/api/v1/auth/login", data=form_payload)
    assert resp_form.status_code == 200
    data_form = resp_form.json()
    assert "access_token" in data_form
    assert data_form["token_type"] == "bearer"


def test_login_wrong_password(unauth_client: TestClient):
    """Test login with incorrect password returns 401 Unauthorized."""
    payload = {
        "email": "user1@example.com",
        "password": "wrongpassword",
    }
    response = unauth_client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"


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
    assert data["role"] == "MEMBER"


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
    """Test RBAC: MEMBER gets 403 Forbidden on Admin endpoint, ADMIN gets 200 OK."""
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
    users_list = resp_admin.json()
    assert isinstance(users_list, list)
    assert len(users_list) >= 2
