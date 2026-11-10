from fastapi import HTTPException, status

from taskhub.core.security import create_access_token, get_password_hash, verify_password
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
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        role_val = user_in.role.value if hasattr(user_in.role, "value") else str(user_in.role)
        user_data = {
            "email": user_in.email,
            "full_name": user_in.full_name,
            "hashed_password": get_password_hash(user_in.password),
            "role": role_val,
        }
        user = await self.user_repo.create(user_data)
        return user

    async def authenticate(self, email: str, password: str) -> User:
        user = await self.user_repo.get_by_email(email=email)
        if user is None or not verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user",
            )

        return user

    def create_user_token(self, user: User) -> Token:
        role_val = user.role.value if hasattr(user.role, "value") else str(user.role)
        payload = {
            "sub": str(user.id),
            "role": role_val,
        }
        access_token = create_access_token(data=payload)
        return Token(access_token=access_token, token_type="bearer")
