from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from taskhub.core.constants import DEFAULT_PAGE_SIZE
from taskhub.core.enums import WorkspaceRole
from taskhub.models.project import Project
from taskhub.repositories.project_repo import ProjectRepository
from taskhub.repositories.workspace_member_repo import WorkspaceMemberRepository
from taskhub.repositories.workspace_repo import WorkspaceRepository
from taskhub.schemas.project import ProjectCreate, ProjectUpdate


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
        workspace = await self.ws_repo.get(workspace_id)
        if workspace is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found",
            )

        is_owner = workspace.owner_id == user_id
        member = await self.member_repo.get_member(workspace_id, user_id)

        if not (is_owner or member is not None):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a member of this workspace",
            )

        is_admin = member is not None and str(member.role).upper() in [
            WorkspaceRole.OWNER.value,
            WorkspaceRole.ADMIN.value,
        ]

        if not (is_owner or is_admin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only workspace OWNER or ADMIN can create projects",
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
        workspace = await self.ws_repo.get(workspace_id)
        if workspace is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found",
            )

        is_owner = workspace.owner_id == user_id
        member = await self.member_repo.get_member(workspace_id, user_id)

        if not (is_owner or member is not None):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a member of this workspace",
            )

        return await self.project_repo.get_by_workspace_paginated(
            workspace_id=workspace_id,
            skip=skip,
            limit=limit,
        )

    async def get_project(self, project_id: int, user_id: int) -> Project:
        project = await self.project_repo.get(project_id)
        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )

        if project.workspace_id is not None:
            workspace = await self.ws_repo.get(project.workspace_id)
            if workspace is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Workspace not found",
                )
            is_ws_owner = workspace.owner_id == user_id
            member = await self.member_repo.get_member(project.workspace_id, user_id)
            if not (is_ws_owner or member is not None or project.owner_id == user_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not a member of this workspace",
                )
        elif project.owner_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: You do not have permission to view this project",
            )

        return project

    async def update_project(
        self,
        project_id: int,
        user_id: int,
        data: ProjectUpdate,
    ) -> Project:
        project = await self.project_repo.get(project_id)
        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )

        is_project_owner = project.owner_id == user_id
        is_ws_owner = False
        is_ws_admin = False

        if project.workspace_id is not None:
            workspace = await self.ws_repo.get(project.workspace_id)
            if workspace and workspace.owner_id == user_id:
                is_ws_owner = True
            member = await self.member_repo.get_member(project.workspace_id, user_id)
            if member and str(member.role).upper() in [
                WorkspaceRole.OWNER.value,
                WorkspaceRole.ADMIN.value,
            ]:
                is_ws_admin = True

        if not (is_project_owner or is_ws_owner or is_ws_admin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied: You do not have permission to update this project",
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
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )

        is_ws_owner = False
        is_ws_admin = False

        if project.workspace_id is not None:
            workspace = await self.ws_repo.get(project.workspace_id)
            if workspace and workspace.owner_id == user_id:
                is_ws_owner = True
            member = await self.member_repo.get_member(project.workspace_id, user_id)
            if member and str(member.role).upper() in [
                WorkspaceRole.OWNER.value,
                WorkspaceRole.ADMIN.value,
            ]:
                is_ws_admin = True

        if not (is_ws_owner or is_ws_admin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only workspace OWNER or ADMIN can delete this project",
            )

        await self.project_repo.remove(project_id)
        await self.db.commit()
        return True
