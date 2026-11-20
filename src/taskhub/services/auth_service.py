from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from starlette.concurrency import run_in_threadpool

from taskhub.core.enums import UserRole
from taskhub.core.exceptions import (
    EmailAlreadyRegisteredError,
    InactiveUserError,
    InvalidCredentialsError,
    InvalidRefreshTokenBadRequestError,
    InvalidRefreshTokenError,
)
from taskhub.core.security import (
    DUMMY_HASH,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from taskhub.models.user import User
from taskhub.repositories.revoked_token_repo import RevokedTokenRepository
from taskhub.repositories.user_repo import UserRepository
from taskhub.schemas.token import Token
from taskhub.schemas.user import UserCreate


class AuthService:
    def __init__(
        self,
        user_repo: UserRepository,
        revoked_token_repo: RevokedTokenRepository,
    ) -> None:
        self.user_repo = user_repo
        self.revoked_token_repo = revoked_token_repo

    async def register(self, user_in: UserCreate) -> User:
        existing_user = await self.user_repo.get_by_email(email=user_in.email)
        if existing_user is not None:
            raise EmailAlreadyRegisteredError()

        hashed_password = await run_in_threadpool(get_password_hash, user_in.password)
        user_data = {
            "email": user_in.email,
            "full_name": user_in.full_name,
            "hashed_password": hashed_password,
            "role": UserRole.MEMBER,
        }
        try:
            user = await self.user_repo.create(user_data)
            await self.user_repo.db.commit()
            return user
        except IntegrityError:
            await self.user_repo.db.rollback()
            raise EmailAlreadyRegisteredError() from None

    async def authenticate(self, email: str, password: str) -> User:
        user = await self.user_repo.get_by_email(email=email)
        if user is None:
            # Constant time verification with dummy hash to prevent timing attack enumeration
            await run_in_threadpool(verify_password, password, DUMMY_HASH)
            raise InvalidCredentialsError()

        is_valid = await run_in_threadpool(verify_password, password, user.hashed_password)
        if not is_valid:
            raise InvalidCredentialsError()

        if not user.is_active:
            raise InactiveUserError()

        return user

    def create_user_token(self, user: User) -> Token:
        role_val = user.role.value if hasattr(user.role, "value") else str(user.role)
        token_version = getattr(user, "token_version", 1)
        access_token = create_access_token(
            user_id=user.id,
            role=role_val,
            token_version=token_version,
        )
        refresh_token = create_refresh_token(
            user_id=user.id,
            role=role_val,
            token_version=token_version,
        )
        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
        )

    async def refresh_token(self, refresh_token_str: str) -> Token:
        payload = decode_token(refresh_token_str)
        if payload is None:
            raise InvalidRefreshTokenError()

        token_type = payload.get("type")
        if token_type != "refresh":
            raise InvalidRefreshTokenError()

        jti = payload.get("jti")
        if not jti or await self.revoked_token_repo.is_revoked(jti):
            raise InvalidRefreshTokenError()

        user_id_str = payload.get("sub")
        if not user_id_str:
            raise InvalidRefreshTokenError()

        try:
            user_id = int(user_id_str)
        except ValueError:
            raise InvalidRefreshTokenError() from None

        user = await self.user_repo.get(user_id)
        if user is None:
            raise InvalidRefreshTokenError()

        if not user.is_active:
            raise InactiveUserError()

        # Token version check: ensures tokens issued prior to a password change are invalid
        token_version = payload.get("token_version")
        if token_version is not None and token_version != user.token_version:
            raise InvalidRefreshTokenError()

        # Token Rotation: Revoke current refresh token jti in DB
        exp_ts = payload.get("exp")
        expires_at = datetime.fromtimestamp(exp_ts, tz=UTC) if exp_ts else None
        await self.revoked_token_repo.revoke(jti=jti, token_type="refresh", expires_at=expires_at)
        await self.user_repo.db.commit()

        # Issue new token pair
        return self.create_user_token(user)

    async def logout(self, current_user: User, refresh_token_str: str) -> None:
        payload = decode_token(refresh_token_str)
        if payload is None:
            raise InvalidRefreshTokenBadRequestError()

        if payload.get("type") != "refresh":
            raise InvalidRefreshTokenBadRequestError()

        if payload.get("sub") != str(current_user.id):
            raise InvalidRefreshTokenBadRequestError()

        jti = payload.get("jti")
        if not jti:
            raise InvalidRefreshTokenBadRequestError()

        exp_ts = payload.get("exp")
        expires_at = datetime.fromtimestamp(exp_ts, tz=UTC) if exp_ts else None
        await self.revoked_token_repo.revoke(jti=jti, token_type="refresh", expires_at=expires_at)
        await self.user_repo.db.commit()
