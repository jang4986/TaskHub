from sqlalchemy.ext.asyncio import AsyncSession

from taskhub.core.constants import DEFAULT_PAGE_SIZE
from taskhub.core.enums import WorkspaceRole
from taskhub.core.exceptions import (
    ProjectAccessDeniedError,
    ProjectNotFoundError,
    WorkspaceAccessDeniedError,
    WorkspaceNotFoundError,
)
from taskhub.models.project import Project
from taskhub.repositories.project_repo import ProjectRepository
from taskhub.repositories.workspace_member_repo import WorkspaceMemberRepository
from taskhub.repositories.workspace_repo import WorkspaceRepository
from taskhub.schemas.project import ProjectCreate, ProjectUpdate
from taskhub.services.workspace_service import require_workspace_role


class ProjectService:
    def __init__(
        self,
        db: AsyncSession,
        project_repo: ProjectRepository,
        ws_repo: WorkspaceRepository,
        member_repo: WorkspaceMemberRepository,
    ) -> None:
        self.db = db
        self.project_repo = project_repo
        self.ws_repo = ws_repo
        self.member_repo = member_repo

    async def create_project(
        self,
        workspace_id: int,
        user_id: int,
        data: ProjectCreate,
    ) -> Project:
        await require_workspace_role(
            workspace_id=workspace_id,
            user_id=user_id,
            allowed_roles={WorkspaceRole.OWNER, WorkspaceRole.ADMIN},
            ws_repo=self.ws_repo,
            member_repo=self.member_repo,
            denied_detail="Only workspace OWNER or ADMIN can create projects",
        )

        project = Project(
            workspace_id=workspace_id,
            owner_id=user_id,
            name=data.name,
            description=data.description,
        )
        self.db.add(project)
        await self.db.commit()
        await self.db.refresh(project)
        return project

    async def list_projects(
        self,
        workspace_id: int,
        user_id: int,
        skip: int = 0,
        limit: int = DEFAULT_PAGE_SIZE,
    ) -> tuple[list[Project], int]:
        await require_workspace_role(
            workspace_id=workspace_id,
            user_id=user_id,
            allowed_roles=None,
            ws_repo=self.ws_repo,
            member_repo=self.member_repo,
            denied_detail="Not a member of this workspace",
        )

        return await self.project_repo.get_by_workspace_paginated(
            workspace_id=workspace_id,
            skip=skip,
            limit=limit,
        )

    async def get_project(self, project_id: int, user_id: int) -> Project:
        project = await self.project_repo.get(project_id)
        if project is None:
            raise ProjectNotFoundError(project_id)

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

        return project

    async def update_project(
        self,
        project_id: int,
        user_id: int,
        data: ProjectUpdate,
    ) -> Project:
        project = await self.project_repo.get(project_id)
        if project is None:
            raise ProjectNotFoundError(project_id)

        has_permission = False
        if project.owner_id == user_id:
            has_permission = True
        elif project.workspace_id is not None:
            try:
                await require_workspace_role(
                    workspace_id=project.workspace_id,
                    user_id=user_id,
                    allowed_roles={WorkspaceRole.OWNER, WorkspaceRole.ADMIN},
                    ws_repo=self.ws_repo,
                    member_repo=self.member_repo,
                )
                has_permission = True
            except (WorkspaceNotFoundError, WorkspaceAccessDeniedError):
                has_permission = False

        if not has_permission:
            raise ProjectAccessDeniedError(
                "Permission denied: You do not have permission to update this project"
            )

        update_dict = data.model_dump(exclude_unset=True)
        if "name" in update_dict and update_dict["name"] is not None:
            project.name = update_dict["name"]
        if "description" in update_dict:
            project.description = update_dict["description"]

        self.db.add(project)
        await self.db.commit()
        await self.db.refresh(project)
        return project

    async def delete_project(self, project_id: int, user_id: int) -> bool:
        project = await self.project_repo.get(project_id)
        if project is None:
            raise ProjectNotFoundError(project_id)

        if project.workspace_id is not None:
            try:
                await require_workspace_role(
                    workspace_id=project.workspace_id,
                    user_id=user_id,
                    allowed_roles={WorkspaceRole.OWNER, WorkspaceRole.ADMIN},
                    ws_repo=self.ws_repo,
                    member_repo=self.member_repo,
                    denied_detail="Only workspace OWNER or ADMIN can delete this project",
                )
            except (WorkspaceNotFoundError, WorkspaceAccessDeniedError):
                raise WorkspaceAccessDeniedError(
                    "Only workspace OWNER or ADMIN can delete this project"
                ) from None
        else:
            raise WorkspaceAccessDeniedError(
                "Only workspace OWNER or ADMIN can delete this project"
            )

        await self.project_repo.remove(project_id)
        await self.db.commit()
        return True
