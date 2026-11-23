from sqlalchemy.ext.asyncio import AsyncSession

from taskhub.core.constants import DEFAULT_PAGE_SIZE
from taskhub.core.enums import ProjectStatus, WorkspaceRole
from taskhub.core.exceptions import (
    ProjectAccessDeniedError,
    ProjectArchivedError,
    ProjectNotFoundError,
    WorkspaceAccessDeniedError,
)
from taskhub.models.project import Project
from taskhub.repositories.project_repo import ProjectRepository
from taskhub.repositories.workspace_member_repo import WorkspaceMemberRepository
from taskhub.repositories.workspace_repo import WorkspaceRepository
from taskhub.schemas.project import ProjectCreate, ProjectUpdate
from taskhub.services.workspace_service import require_workspace_role


def ensure_project_writable(
    project: Project,
    detail: str = "Cannot modify tasks in an archived project",
) -> None:
    """Validate that the project is not in ARCHIVED status."""
    if project.status == ProjectStatus.ARCHIVED or project.status == ProjectStatus.ARCHIVED.value:
        raise ProjectArchivedError(detail)


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
            allowed_roles={WorkspaceRole.OWNER, WorkspaceRole.EDITOR, WorkspaceRole.ADMIN},
            ws_repo=self.ws_repo,
            member_repo=self.member_repo,
            denied_detail="Only workspace OWNER or ADMIN can create projects",
        )

        project = Project(
            workspace_id=workspace_id,
            owner_id=user_id,
            name=data.name,
            description=data.description,
            status=ProjectStatus.ACTIVE.value,
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
        include_archived: bool = False,
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
            include_archived=include_archived,
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

        if project.workspace_id is not None:
            await require_workspace_role(
                workspace_id=project.workspace_id,
                user_id=user_id,
                allowed_roles={WorkspaceRole.OWNER, WorkspaceRole.EDITOR, WorkspaceRole.ADMIN},
                ws_repo=self.ws_repo,
                member_repo=self.member_repo,
                denied_detail="Only workspace OWNER or EDITOR can update this project",
            )
        elif project.owner_id != user_id:
            raise ProjectAccessDeniedError(
                "Permission denied: You do not have permission to update this project"
            )

        update_dict = data.model_dump(exclude_unset=True)

        # Enforce ARCHIVED state restrictions: If currently ARCHIVED,
        # only un-archiving to ACTIVE is allowed; modifying other fields raises error.
        is_archived = (
            project.status == ProjectStatus.ARCHIVED
            or project.status == ProjectStatus.ARCHIVED.value
        )
        if is_archived:
            if set(update_dict.keys()) != {"status"} or update_dict.get("status") not in (
                ProjectStatus.ACTIVE,
                ProjectStatus.ACTIVE.value,
            ):
                raise ProjectArchivedError("Cannot modify an archived project")

        if "name" in update_dict and update_dict["name"] is not None:
            project.name = update_dict["name"]
        if "description" in update_dict:
            project.description = update_dict["description"]
        if "status" in update_dict and update_dict["status"] is not None:
            status_val = (
                update_dict["status"].value
                if hasattr(update_dict["status"], "value")
                else str(update_dict["status"])
            )
            project.status = status_val

        self.db.add(project)
        await self.db.commit()
        await self.db.refresh(project)
        return project

    async def delete_project(self, project_id: int, user_id: int) -> bool:
        project = await self.project_repo.get(project_id)
        if project is None:
            raise ProjectNotFoundError(project_id)

        if project.workspace_id is not None:
            await require_workspace_role(
                workspace_id=project.workspace_id,
                user_id=user_id,
                allowed_roles={WorkspaceRole.OWNER, WorkspaceRole.ADMIN},
                ws_repo=self.ws_repo,
                member_repo=self.member_repo,
                denied_detail="Only workspace OWNER or ADMIN can delete this project",
            )
        else:
            raise WorkspaceAccessDeniedError(
                "Only workspace OWNER or ADMIN can delete this project"
            )

        await self.project_repo.remove(project_id)
        await self.db.commit()
        return True
