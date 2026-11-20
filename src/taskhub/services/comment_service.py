from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from taskhub.core.constants import DEFAULT_PAGE_SIZE
from taskhub.core.enums import ProjectStatus, WorkspaceRole
from taskhub.core.exceptions import (
    CommentAccessDeniedError,
    CommentNotFoundError,
    ProjectAccessDeniedError,
    ProjectNotFoundError,
    TaskNotFoundError,
    WorkspaceAccessDeniedError,
    WorkspaceNotFoundError,
)
from taskhub.models.comment import Comment
from taskhub.repositories.comment_repo import CommentRepository
from taskhub.repositories.project_repo import ProjectRepository
from taskhub.repositories.task_repo import TaskRepository
from taskhub.repositories.workspace_member_repo import WorkspaceMemberRepository
from taskhub.repositories.workspace_repo import WorkspaceRepository
from taskhub.schemas.comment import CommentCreate
from taskhub.services.workspace_service import require_workspace_role


class CommentService:
    def __init__(
        self,
        db: AsyncSession,
        comment_repo: CommentRepository,
        task_repo: TaskRepository,
        project_repo: ProjectRepository,
        ws_repo: WorkspaceRepository,
        member_repo: WorkspaceMemberRepository,
    ) -> None:
        self.db = db
        self.comment_repo = comment_repo
        self.task_repo = task_repo
        self.project_repo = project_repo
        self.ws_repo = ws_repo
        self.member_repo = member_repo

    async def check_task_read_access(self, task_id: int, user_id: int):
        task = await self.task_repo.get(task_id)
        if task is None:
            raise TaskNotFoundError(task_id)

        project = await self.project_repo.get(task.project_id)
        if project is None:
            raise ProjectNotFoundError(task.project_id)

        if project.owner_id == user_id:
            return task, project

        if project.workspace_id is not None:
            await require_workspace_role(
                workspace_id=project.workspace_id,
                user_id=user_id,
                allowed_roles=None,
                ws_repo=self.ws_repo,
                member_repo=self.member_repo,
                denied_detail="Not a member of this workspace",
            )
            return task, project

        raise ProjectAccessDeniedError()

    async def create_comment(
        self,
        task_id: int,
        author_id: int,
        data: CommentCreate,
    ) -> Comment:
        task, project = await self.check_task_read_access(task_id, author_id)

        project_status_val = (
            project.status.value if hasattr(project.status, "value") else str(project.status)
        )
        if project_status_val == ProjectStatus.ARCHIVED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot comment on tasks in an archived project",
            )

        comment = Comment(
            task_id=task_id,
            author_id=author_id,
            content=data.content,
        )
        self.db.add(comment)
        await self.db.commit()

        loaded = await self.comment_repo.get_with_author(comment.id)
        return loaded or comment

    async def list_task_comments(
        self,
        task_id: int,
        user_id: int,
        skip: int = 0,
        limit: int = DEFAULT_PAGE_SIZE,
    ) -> tuple[list[Comment], int]:
        await self.check_task_read_access(task_id, user_id)
        return await self.comment_repo.get_by_task_paginated(task_id, skip=skip, limit=limit)

    async def list_comments(
        self,
        task_id: int,
        user_id: int,
        skip: int = 0,
        limit: int = DEFAULT_PAGE_SIZE,
    ) -> tuple[list[Comment], int]:
        return await self.list_task_comments(
            task_id=task_id,
            user_id=user_id,
            skip=skip,
            limit=limit,
        )

    async def delete_comment(self, comment_id: int, user_id: int) -> bool:
        comment = await self.comment_repo.get(comment_id)
        if comment is None:
            raise CommentNotFoundError(comment_id)

        task = await self.task_repo.get(comment.task_id)
        if task is None:
            raise TaskNotFoundError(comment.task_id)

        project = await self.project_repo.get(task.project_id)
        if project is None:
            raise ProjectNotFoundError(task.project_id)

        # Verify caller has at least membership/read access to the project
        try:
            if project.workspace_id is not None:
                await require_workspace_role(
                    workspace_id=project.workspace_id,
                    user_id=user_id,
                    allowed_roles=None,
                    ws_repo=self.ws_repo,
                    member_repo=self.member_repo,
                    denied_detail="Not a member of this workspace",
                )
            elif project.owner_id != user_id:
                raise ProjectAccessDeniedError()
        except (ProjectAccessDeniedError, WorkspaceAccessDeniedError):
            raise CommentNotFoundError(comment_id) from None

        # Author can delete their own comment provided they are an active workspace member
        if comment.author_id == user_id:
            await self.comment_repo.remove(comment_id)
            await self.db.commit()
            return True

        # Otherwise, only workspace OWNER (or personal project owner) can delete comments
        is_ws_owner = False
        if project.owner_id == user_id:
            is_ws_owner = True
        elif project.workspace_id is not None:
            try:
                await require_workspace_role(
                    workspace_id=project.workspace_id,
                    user_id=user_id,
                    allowed_roles={WorkspaceRole.OWNER},
                    ws_repo=self.ws_repo,
                    member_repo=self.member_repo,
                )
                is_ws_owner = True
            except (WorkspaceAccessDeniedError, WorkspaceNotFoundError):
                is_ws_owner = False

        if not is_ws_owner:
            raise CommentAccessDeniedError("You do not have permission to delete this comment")

        await self.comment_repo.remove(comment_id)
        await self.db.commit()
        return True
