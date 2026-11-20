from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Query
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from taskhub.core.config import settings
from taskhub.core.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from taskhub.core.enums import UserRole
from taskhub.core.exceptions import (
    CredentialsValidationError,
    InactiveUserError,
    InsufficientPrivilegesError,
)
from taskhub.core.security import decode_access_token
from taskhub.db.session import get_db
from taskhub.models.user import User
from taskhub.repositories.comment_repo import CommentRepository
from taskhub.repositories.label_repo import LabelRepository
from taskhub.repositories.project_repo import ProjectRepository
from taskhub.repositories.revoked_token_repo import RevokedTokenRepository
from taskhub.repositories.task_repo import TaskRepository
from taskhub.repositories.user_repo import UserRepository
from taskhub.repositories.workspace_member_repo import WorkspaceMemberRepository
from taskhub.repositories.workspace_repo import WorkspaceRepository
from taskhub.services.auth_service import AuthService
from taskhub.services.comment_service import CommentService
from taskhub.services.label_service import LabelService
from taskhub.services.project_service import ProjectService
from taskhub.services.task_service import TaskService
from taskhub.services.user_service import UserService
from taskhub.services.workspace_service import WorkspaceService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


class PaginationParams:
    def __init__(
        self,
        page: Annotated[int, Query(ge=1, description="Page number")] = 1,
        limit: Annotated[
            int,
            Query(
                ge=1,
                le=MAX_PAGE_SIZE,
                description="Max number of items to return",
            ),
        ] = DEFAULT_PAGE_SIZE,
        skip: Annotated[int | None, Query(ge=0, description="Number of items to skip")] = None,
    ) -> None:
        self.page = page
        self.limit = limit
        self.skip = skip

    @property
    def offset(self) -> int:
        return self.skip if self.skip is not None else (self.page - 1) * self.limit


# Dependency provider functions
def get_user_repo(db: Annotated[AsyncSession, Depends(get_db)]) -> UserRepository:
    return UserRepository(db=db)


def get_task_repo(db: Annotated[AsyncSession, Depends(get_db)]) -> TaskRepository:
    return TaskRepository(db=db)


def get_workspace_repo(db: Annotated[AsyncSession, Depends(get_db)]) -> WorkspaceRepository:
    return WorkspaceRepository(db=db)


def get_workspace_member_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WorkspaceMemberRepository:
    return WorkspaceMemberRepository(db=db)


def get_project_repo(db: Annotated[AsyncSession, Depends(get_db)]) -> ProjectRepository:
    return ProjectRepository(db=db)


def get_label_repo(db: Annotated[AsyncSession, Depends(get_db)]) -> LabelRepository:
    return LabelRepository(db=db)


def get_comment_repo(db: Annotated[AsyncSession, Depends(get_db)]) -> CommentRepository:
    return CommentRepository(db=db)


def get_revoked_token_repo(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RevokedTokenRepository:
    return RevokedTokenRepository(db=db)


def get_auth_service(
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
    revoked_token_repo: Annotated[RevokedTokenRepository, Depends(get_revoked_token_repo)],
) -> AuthService:
    return AuthService(user_repo=user_repo, revoked_token_repo=revoked_token_repo)


def get_user_service(
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
) -> UserService:
    return UserService(user_repo=user_repo)


def get_task_service(
    repo: Annotated[TaskRepository, Depends(get_task_repo)],
    project_repo: Annotated[ProjectRepository, Depends(get_project_repo)],
    ws_repo: Annotated[WorkspaceRepository, Depends(get_workspace_repo)],
    member_repo: Annotated[WorkspaceMemberRepository, Depends(get_workspace_member_repo)],
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
) -> TaskService:
    return TaskService(
        task_repo=repo,
        project_repo=project_repo,
        ws_repo=ws_repo,
        member_repo=member_repo,
        user_repo=user_repo,
    )


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


def get_label_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    label_repo: Annotated[LabelRepository, Depends(get_label_repo)],
    project_repo: Annotated[ProjectRepository, Depends(get_project_repo)],
    task_repo: Annotated[TaskRepository, Depends(get_task_repo)],
    ws_repo: Annotated[WorkspaceRepository, Depends(get_workspace_repo)],
    member_repo: Annotated[WorkspaceMemberRepository, Depends(get_workspace_member_repo)],
) -> LabelService:
    return LabelService(
        db=db,
        label_repo=label_repo,
        project_repo=project_repo,
        task_repo=task_repo,
        ws_repo=ws_repo,
        member_repo=member_repo,
    )


def get_comment_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    comment_repo: Annotated[CommentRepository, Depends(get_comment_repo)],
    task_repo: Annotated[TaskRepository, Depends(get_task_repo)],
    project_repo: Annotated[ProjectRepository, Depends(get_project_repo)],
    ws_repo: Annotated[WorkspaceRepository, Depends(get_workspace_repo)],
    member_repo: Annotated[WorkspaceMemberRepository, Depends(get_workspace_member_repo)],
) -> CommentService:
    return CommentService(
        db=db,
        comment_repo=comment_repo,
        task_repo=task_repo,
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

    if payload.get("type") != "access":
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

    token_version = payload.get("token_version")
    if token_version is not None and token_version != user.token_version:
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
RevokedTokenRepo = Annotated[RevokedTokenRepository, Depends(get_revoked_token_repo)]
TaskRepo = Annotated[TaskRepository, Depends(get_task_repo)]
ProjectRepo = Annotated[ProjectRepository, Depends(get_project_repo)]
LabelRepo = Annotated[LabelRepository, Depends(get_label_repo)]
CommentRepo = Annotated[CommentRepository, Depends(get_comment_repo)]
WorkspaceRepo = Annotated[WorkspaceRepository, Depends(get_workspace_repo)]
WorkspaceMemberRepo = Annotated[WorkspaceMemberRepository, Depends(get_workspace_member_repo)]
AuthServ = Annotated[AuthService, Depends(get_auth_service)]
UserServ = Annotated[UserService, Depends(get_user_service)]
TaskServ = Annotated[TaskService, Depends(get_task_service)]
ProjectServ = Annotated[ProjectService, Depends(get_project_service)]
LabelServ = Annotated[LabelService, Depends(get_label_service)]
CommentServ = Annotated[CommentService, Depends(get_comment_service)]
WorkspaceServ = Annotated[WorkspaceService, Depends(get_workspace_service)]
CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentActiveUser = Annotated[User, Depends(get_current_active_user)]
Pagination = Annotated[PaginationParams, Depends()]
