from sqlalchemy.exc import IntegrityError
from starlette.concurrency import run_in_threadpool

from taskhub.core.enums import UserRole
from taskhub.core.exceptions import (
    EmailAlreadyRegisteredError,
    InactiveUserError,
    InvalidCredentialsError,
)
from taskhub.core.security import (
    DUMMY_HASH,
    create_access_token,
    get_password_hash,
    verify_password,
)
from taskhub.models.user import User
from taskhub.repositories.user_repo import UserRepository
from taskhub.schemas.token import Token
from taskhub.schemas.user import UserCreate


class AuthService:
    def __init__(self, user_repo: UserRepository) -> None:
        self.user_repo = user_repo

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
            raise EmailAlreadyRegisteredError()

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
        access_token = create_access_token(
            user_id=user.id,
            role=role_val,
        )
        return Token(access_token=access_token, token_type="bearer")
