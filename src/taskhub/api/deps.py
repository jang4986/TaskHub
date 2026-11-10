from collections.abc import Callable
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from taskhub.core.config import settings
from taskhub.core.security import decode_access_token
from taskhub.db.session import get_db
from taskhub.enums.common import UserRole
from taskhub.models.user import User
from taskhub.repositories.task_repo import TaskRepository
from taskhub.repositories.user_repo import UserRepository
from taskhub.services.auth_service import AuthService
from taskhub.services.task_service import TaskService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


def get_user_repo(db: AsyncSession = Depends(get_db)) -> UserRepository:
    return UserRepository(db=db)


def get_auth_service(
    user_repo: UserRepository = Depends(get_user_repo),
) -> AuthService:
    return AuthService(user_repo=user_repo)


def get_task_repo(db: AsyncSession = Depends(get_db)) -> TaskRepository:
    return TaskRepository(db=db)


def get_task_service(
    repo: TaskRepository = Depends(get_task_repo),
) -> TaskService:
    return TaskService(task_repo=repo)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    user_id_str: Optional[str] = payload.get("sub")
    if user_id_str is None:
        raise credentials_exception

    try:
        user_id = int(user_id_str)
    except ValueError:
        raise credentials_exception

    user_repo = UserRepository(db=db)
    user = await user_repo.get(user_id)
    if user is None:
        raise credentials_exception

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )
    return current_user


def require_roles(allowed_roles: list[UserRole]) -> Callable:
    async def role_checker(
        current_user: User = Depends(get_current_active_user),
    ) -> User:
        allowed_values = [
            r.value if hasattr(r, "value") else str(r) for r in allowed_roles
        ]
        user_role_val = (
            current_user.role.value
            if hasattr(current_user.role, "value")
            else str(current_user.role)
        )
        if user_role_val not in allowed_values:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="The user doesn't have enough privileges",
            )
        return current_user

    return role_checker
