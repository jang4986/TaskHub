from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Union
import uuid
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
    user_id: Union[int, str],
    role: str,
    expires_delta: Optional[timedelta] = None,
    extra_claims: Optional[dict[str, Any]] = None,
) -> str:
    now = datetime.now(timezone.utc)
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


def decode_access_token(token: str) -> Optional[dict[str, Any]]:
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        return payload
    except PyJWTError:
        return None
