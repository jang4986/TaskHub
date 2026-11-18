import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from jwt.exceptions import PyJWTError
from pwdlib import PasswordHash

from taskhub.core.config import settings

password_hasher = PasswordHash.recommended()
# Pre-computed dummy hash to mitigate timing attacks when user is not found
DUMMY_HASH: str = password_hasher.hash("dummy_fallback_password_for_timing_mitigation")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hasher.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return password_hasher.hash(password)


def create_access_token(
    user_id: int | str,
    role: str,
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    now = datetime.now(UTC)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    claims: dict[str, Any] = {
        "sub": str(user_id),
        "role": str(role),
        "type": "access",
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": expire,
    }
    if extra_claims:
        claims.update(extra_claims)

    encoded_jwt = jwt.encode(
        claims,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    return encoded_jwt


def create_refresh_token(
    user_id: int | str,
    role: str,
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    now = datetime.now(UTC)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    claims: dict[str, Any] = {
        "sub": str(user_id),
        "role": str(role),
        "type": "refresh",
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": expire,
    }
    if extra_claims:
        claims.update(extra_claims)

    encoded_jwt = jwt.encode(
        claims,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    return encoded_jwt


# In-memory revocation store: maps jti -> expiration timestamp (seconds)
# Allows standalone Pytest runs without requiring external Redis cache
_revoked_tokens: dict[str, float] = {}


async def revoke_token(jti: str, exp: int | float | None = None) -> None:
    now_ts = datetime.now(UTC).timestamp()
    if exp is not None:
        exp_ts = float(exp)
    else:
        exp_ts = now_ts + (settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400)
    _revoked_tokens[jti] = exp_ts


async def is_token_revoked(jti: str) -> bool:
    now_ts = datetime.now(UTC).timestamp()
    exp_ts = _revoked_tokens.get(jti)
    if exp_ts is None:
        return False
    if exp_ts < now_ts:
        _revoked_tokens.pop(jti, None)
        return False
    return True


def clear_revoked_tokens() -> None:
    """Helper to reset token revocation store between tests."""
    _revoked_tokens.clear()


def decode_token(token: str) -> dict[str, Any] | None:
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        return payload
    except PyJWTError:
        return None


def decode_access_token(token: str) -> dict[str, Any] | None:
    return decode_token(token)
