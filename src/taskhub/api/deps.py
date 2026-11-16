from collections.abc import Callable
from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from taskhub.core.config import settings
from taskhub.core.enums import UserRole
from taskhub.core.exceptions import (
    CredentialsValidationError,
    InactiveUserError,
    InsufficientPrivilegesError,
)
from taskhub.core.security import decode_access_token
from taskhub.db.session import get_db
from taskhub.models.user import User
from taskhub.repositories.project_repo import ProjectRepository
from taskhub.repositories.task_repo import TaskRepository
from taskhub.repositories.user_repo import UserRepository
from taskhub.repositories.workspace_member_repo import WorkspaceMemberRepository
from taskhub.repositories.workspace_repo import WorkspaceRepository
from taskhub.services.auth_service import AuthService
from taskhub.services.project_service import ProjectService
from taskhub.services.task_service import TaskService
from taskhub.services.workspace_service import WorkspaceService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


# Dependency provider functions
def get_user_repo(db: Annotated[AsyncSession, Depends(get_db)]) -> UserRepository:
    return UserRepository(db=db)


def get_auth_service(
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
) -> AuthService:
    return AuthService(user_repo=user_repo)


def get_task_repo(db: Annotated[AsyncSession, Depends(get_db)]) -> TaskRepository:
    return TaskRepository(db=db)


def get_task_service(
    repo: Annotated[TaskRepository, Depends(get_task_repo)],
) -> TaskService:
    return TaskService(task_repo=repo)


def get_workspace_repo(db: Annotated[AsyncSession, Depends(get_db)]) -> WorkspaceRepository:
    return WorkspaceRepository(db=db)


def get_workspace_member_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WorkspaceMemberRepository:
    return WorkspaceMemberRepository(db=db)


def get_workspace_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    ws_repo: Annotated[WorkspaceRepository, Depends(get_workspace_repo)],
    member_repo: Annotated[WorkspaceMemberRepository, Depends(get_workspace_member_repo)],
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
) -> WorkspaceService:
    return WorkspaceService(
        db=db,
        ws_repo=ws_repo,
        member_repo=member_repo,
        user_repo=user_repo,
    )


def get_project_repo(db: Annotated[AsyncSession, Depends(get_db)]) -> ProjectRepository:
    return ProjectRepository(db=db)


def get_project_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    project_repo: Annotated[ProjectRepository, Depends(get_project_repo)],
    ws_repo: Annotated[WorkspaceRepository, Depends(get_workspace_repo)],
    member_repo: Annotated[WorkspaceMemberRepository, Depends(get_workspace_member_repo)],
) -> ProjectService:
    return ProjectService(
        db=db,
        project_repo=project_repo,
        ws_repo=ws_repo,
        member_repo=member_repo,
    )


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    payload = decode_access_token(token)
    if payload is None:
        raise CredentialsValidationError()

    user_id_str: str | None = payload.get("sub")
    if user_id_str is None:
        raise CredentialsValidationError()

    try:
        user_id = int(user_id_str)
    except ValueError:
        raise CredentialsValidationError() from None

    user_repo = UserRepository(db=db)
    user = await user_repo.get(user_id)
    if user is None:
        raise CredentialsValidationError()

    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if not current_user.is_active:
        raise InactiveUserError()
    return current_user


def require_roles(allowed_roles: list[UserRole]) -> Callable:
    async def role_checker(
        current_user: Annotated[User, Depends(get_current_active_user)],
    ) -> User:
        if current_user.role not in allowed_roles:
            raise InsufficientPrivilegesError()
        return current_user

    return role_checker


# Type aliases using Annotated for clean, modern injection
DbSession = Annotated[AsyncSession, Depends(get_db)]
UserRepo = Annotated[UserRepository, Depends(get_user_repo)]
TaskRepo = Annotated[TaskRepository, Depends(get_task_repo)]
ProjectRepo = Annotated[ProjectRepository, Depends(get_project_repo)]
WorkspaceRepo = Annotated[WorkspaceRepository, Depends(get_workspace_repo)]
WorkspaceMemberRepo = Annotated[WorkspaceMemberRepository, Depends(get_workspace_member_repo)]
AuthServ = Annotated[AuthService, Depends(get_auth_service)]
TaskServ = Annotated[TaskService, Depends(get_task_service)]
ProjectServ = Annotated[ProjectService, Depends(get_project_service)]
WorkspaceServ = Annotated[WorkspaceService, Depends(get_workspace_service)]
CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentActiveUser = Annotated[User, Depends(get_current_active_user)]
