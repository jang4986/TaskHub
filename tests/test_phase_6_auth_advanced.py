from fastapi.testclient import TestClient

from taskhub.core.enums import UserRole
from taskhub.core.security import (
    create_refresh_token,
    decode_token,
)


def test_login_returns_refresh_token(unauth_client: TestClient):
    """Test login via OAuth2 form returns both access_token and refresh_token with proper claims."""
    form_payload = {
        "username": "user1@example.com",
        "password": "password123",
    }
    response = unauth_client.post("/api/v1/auth/login", data=form_payload)
    assert response.status_code == 200

    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"

    # Decode and check access_token claims
    access_payload = decode_token(data["access_token"])
    assert access_payload is not None
    assert access_payload["sub"] == "1"
    assert access_payload["role"] == UserRole.MEMBER.value
    assert access_payload["type"] == "access"
    assert "jti" in access_payload
    assert "exp" in access_payload

    # Decode and check refresh_token claims
    refresh_payload = decode_token(data["refresh_token"])
    assert refresh_payload is not None
    assert refresh_payload["sub"] == "1"
    assert refresh_payload["role"] == UserRole.MEMBER.value
    assert refresh_payload["type"] == "refresh"
    assert "jti" in refresh_payload
    assert "exp" in refresh_payload
    assert access_payload["jti"] != refresh_payload["jti"]


def test_refresh_token_success_and_rotation(unauth_client: TestClient):
    """Test refresh token rotation: old refresh token is revoked upon rotation."""
    # 1. Login to get initial tokens
    login_resp = unauth_client.post(
        "/api/v1/auth/login",
        data={"username": "user1@example.com", "password": "password123"},
    )
    assert login_resp.status_code == 200
    initial_tokens = login_resp.json()
    initial_access_token = initial_tokens["access_token"]
    initial_refresh_token = initial_tokens["refresh_token"]

    # 2. Use initial_refresh_token to obtain new tokens
    refresh_resp = unauth_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": initial_refresh_token},
    )
    assert refresh_resp.status_code == 200
    new_tokens = refresh_resp.json()
    assert "access_token" in new_tokens
    assert "refresh_token" in new_tokens
    assert new_tokens["token_type"] == "bearer"

    # Verify new tokens are distinct (rotated)
    assert new_tokens["access_token"] != initial_access_token
    assert new_tokens["refresh_token"] != initial_refresh_token

    # 3. Use new_access_token to access protected endpoint
    me_resp = unauth_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {new_tokens['access_token']}"},
    )
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "user1@example.com"

    # 4. Attempt to reuse old initial_refresh_token -> 401 Unauthorized
    reuse_resp = unauth_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": initial_refresh_token},
    )
    assert reuse_resp.status_code == 401
    assert reuse_resp.json()["detail"] == "Invalid or expired refresh token"


def test_refresh_with_access_token_fails(unauth_client: TestClient):
    """Test calling /auth/refresh with an access_token is rejected with 401."""
    login_resp = unauth_client.post(
        "/api/v1/auth/login",
        data={"username": "user1@example.com", "password": "password123"},
    )
    assert login_resp.status_code == 200
    access_token = login_resp.json()["access_token"]

    # Provide access token instead of refresh token
    response = unauth_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": access_token},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired refresh token"


def test_refresh_with_invalid_token_fails(unauth_client: TestClient):
    """Test calling /auth/refresh with invalid string or wrong signature returns 401."""
    response = unauth_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "invalid.jwt.token.string"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired refresh token"


def test_refresh_with_inactive_user_fails(unauth_client: TestClient):
    """Test refresh token for an inactive user returns 403 Forbidden."""
    # User 100 is seeded with is_active=False in conftest.py
    inactive_refresh_token = create_refresh_token(user_id=100, role=UserRole.MEMBER.value)

    response = unauth_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": inactive_refresh_token},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Inactive user"


def test_logout_revokes_refresh_token(unauth_client: TestClient):
    """Test logout revokes the refresh token so subsequent refresh attempts fail with 401."""
    # 1. Login
    login_resp = unauth_client.post(
        "/api/v1/auth/login",
        data={"username": "user1@example.com", "password": "password123"},
    )
    assert login_resp.status_code == 200
    tokens = login_resp.json()
    access_token = tokens["access_token"]
    refresh_token = tokens["refresh_token"]

    # 2. Call logout with valid bearer access token and own refresh token
    logout_resp = unauth_client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"refresh_token": refresh_token},
    )
    assert logout_resp.status_code == 204

    # 3. Verify refresh token is revoked
    refresh_resp = unauth_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_resp.status_code == 401
    assert refresh_resp.json()["detail"] == "Invalid or expired refresh token"


def test_logout_without_auth_fails(unauth_client: TestClient):
    """Test calling /auth/logout without bearer token fails with 401 Unauthorized."""
    response = unauth_client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": "some-token"},
    )
    assert response.status_code == 401


def test_logout_with_another_user_refresh_token_fails(unauth_client: TestClient):
    """Test user cannot revoke another user's refresh token (fails with 400 Bad Request)."""
    # User 1 login
    resp1 = unauth_client.post(
        "/api/v1/auth/login",
        data={"username": "user1@example.com", "password": "password123"},
    )
    user1_access_token = resp1.json()["access_token"]

    # User 2 login
    resp2 = unauth_client.post(
        "/api/v1/auth/login",
        data={"username": "user2@example.com", "password": "password123"},
    )
    user2_refresh_token = resp2.json()["refresh_token"]

    # User 1 attempts to logout passing User 2's refresh token
    logout_resp = unauth_client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {user1_access_token}"},
        json={"refresh_token": user2_refresh_token},
    )
    assert logout_resp.status_code == 400
    assert logout_resp.json()["detail"] == "Invalid refresh token"

    # User 2's refresh token is unaffected and still works
    refresh_resp = unauth_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": user2_refresh_token},
    )
    assert refresh_resp.status_code == 200


def test_get_and_update_user_profile(unauth_client: TestClient):
    """Test GET /auth/me and PATCH /users/me for viewing and updating profile info."""
    login_resp = unauth_client.post(
        "/api/v1/auth/login",
        data={"username": "user1@example.com", "password": "password123"},
    )
    assert login_resp.status_code == 200
    access_token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # 1. Get current profile via canonical /auth/me
    get_resp = unauth_client.get("/api/v1/auth/me", headers=headers)
    assert get_resp.status_code == 200
    user_data = get_resp.json()
    assert user_data["email"] == "user1@example.com"
    original_name = user_data["full_name"]

    # 2. Update full_name
    patch_resp = unauth_client.patch(
        "/api/v1/users/me",
        headers=headers,
        json={"full_name": "Updated User One"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["full_name"] == "Updated User One"

    # 3. Verify persistence
    verify_resp = unauth_client.get("/api/v1/auth/me", headers=headers)
    assert verify_resp.status_code == 200
    assert verify_resp.json()["full_name"] == "Updated User One"

    # 4. Validation error on empty name
    bad_patch = unauth_client.patch(
        "/api/v1/users/me",
        headers=headers,
        json={"full_name": ""},
    )
    assert bad_patch.status_code == 422

    # Restore original name
    unauth_client.patch(
        "/api/v1/users/me",
        headers=headers,
        json={"full_name": original_name},
    )


def test_change_password_success(unauth_client: TestClient):
    """Test change password lifecycle: updates hash, invalidates old pass, allows new pass."""
    # 1. Login user2
    login_resp = unauth_client.post(
        "/api/v1/auth/login",
        data={"username": "user2@example.com", "password": "password123"},
    )
    assert login_resp.status_code == 200
    access_token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # 2. Change password
    change_resp = unauth_client.post(
        "/api/v1/users/change-password",
        headers=headers,
        json={
            "current_password": "password123",
            "new_password": "brandnewpassword789",
        },
    )
    assert change_resp.status_code == 200
    assert change_resp.json()["detail"] == "Password updated successfully"

    # 3. Old password fails
    old_login = unauth_client.post(
        "/api/v1/auth/login",
        data={"username": "user2@example.com", "password": "password123"},
    )
    assert old_login.status_code == 401
    assert old_login.json()["detail"] == "Incorrect email or password"

    # 4. New password succeeds
    new_login = unauth_client.post(
        "/api/v1/auth/login",
        data={"username": "user2@example.com", "password": "brandnewpassword789"},
    )
    assert new_login.status_code == 200
    assert "access_token" in new_login.json()

    # 5. Restore user2 password to password123 for test idempotency
    new_token = new_login.json()["access_token"]
    restore_resp = unauth_client.post(
        "/api/v1/users/change-password",
        headers={"Authorization": f"Bearer {new_token}"},
        json={
            "current_password": "brandnewpassword789",
            "new_password": "password123",
        },
    )
    assert restore_resp.status_code == 200


def test_change_password_wrong_current(unauth_client: TestClient):
    """Test change password fails with 400 when current password is wrong."""
    login_resp = unauth_client.post(
        "/api/v1/auth/login",
        data={"username": "user1@example.com", "password": "password123"},
    )
    assert login_resp.status_code == 200
    access_token = login_resp.json()["access_token"]

    response = unauth_client.post(
        "/api/v1/users/change-password",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "current_password": "wrongpassword999",
            "new_password": "newsecretpassword123",
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Incorrect current password"


def test_change_password_same_password(unauth_client: TestClient):
    """Test change password fails with 400 when new password is identical to current password."""
    login_resp = unauth_client.post(
        "/api/v1/auth/login",
        data={"username": "user1@example.com", "password": "password123"},
    )
    assert login_resp.status_code == 200
    access_token = login_resp.json()["access_token"]

    response = unauth_client.post(
        "/api/v1/users/change-password",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "current_password": "password123",
            "new_password": "password123",
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "New password cannot be the same as current password"


def test_password_change_invalidates_all_existing_tokens(unauth_client: TestClient):
    """Test changing password increments token_version and invalidates prior tokens."""
    # 1. Login user2 to obtain initial tokens
    login_resp = unauth_client.post(
        "/api/v1/auth/login",
        data={"username": "user2@example.com", "password": "password123"},
    )
    assert login_resp.status_code == 200
    old_tokens = login_resp.json()
    old_access_token = old_tokens["access_token"]
    old_refresh_token = old_tokens["refresh_token"]

    # Verify old access token works before password change
    me_resp = unauth_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {old_access_token}"},
    )
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "user2@example.com"

    # 2. Change password
    change_resp = unauth_client.post(
        "/api/v1/users/change-password",
        headers={"Authorization": f"Bearer {old_access_token}"},
        json={
            "current_password": "password123",
            "new_password": "securepassword999",
        },
    )
    assert change_resp.status_code == 200

    # 3. Old access token MUST now fail with 401 (token_version mismatch)
    old_access_check = unauth_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {old_access_token}"},
    )
    assert old_access_check.status_code == 401

    # 4. Old refresh token MUST now fail with 401 (token_version mismatch)
    old_refresh_check = unauth_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh_token},
    )
    assert old_refresh_check.status_code == 401

    # 5. Login with new password succeeds and gets new token_version
    new_login = unauth_client.post(
        "/api/v1/auth/login",
        data={"username": "user2@example.com", "password": "securepassword999"},
    )
    assert new_login.status_code == 200
    new_tokens = new_login.json()
    new_access_token = new_tokens["access_token"]
    new_refresh_token = new_tokens["refresh_token"]

    # 6. New access token works
    new_me = unauth_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {new_access_token}"},
    )
    assert new_me.status_code == 200

    # 7. New refresh token works and can be refreshed
    new_refresh = unauth_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": new_refresh_token},
    )
    assert new_refresh.status_code == 200
    rotated_tokens = new_refresh.json()

    # 8. Restore password back to password123 for test idempotency
    restore_resp = unauth_client.post(
        "/api/v1/users/change-password",
        headers={"Authorization": f"Bearer {rotated_tokens['access_token']}"},
        json={
            "current_password": "securepassword999",
            "new_password": "password123",
        },
    )
    assert restore_resp.status_code == 200
