import re
import unicodedata

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from taskhub.core.constants import DEFAULT_PAGE_SIZE
from taskhub.core.enums import WorkspaceRole
from taskhub.models.workspace import Workspace
from taskhub.models.workspace_member import WorkspaceMember
from taskhub.repositories.user_repo import UserRepository
from taskhub.repositories.workspace_member_repo import WorkspaceMemberRepository
from taskhub.repositories.workspace_repo import WorkspaceRepository
from taskhub.schemas.workspace import WorkspaceCreate, WorkspaceUpdate
from taskhub.schemas.workspace_member import WorkspaceMemberAdd


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^\w\s-]", "", text.lower()).strip()
    slug = re.sub(r"[-\s]+", "-", slug)
    return slug or "workspace"


class WorkspaceService:
    def __init__(
        self,
        db: AsyncSession,
        ws_repo: WorkspaceRepository,
        member_repo: WorkspaceMemberRepository,
        user_repo: UserRepository,
    ) -> None:
        self.db = db
        self.ws_repo = ws_repo
        self.member_repo = member_repo
        self.user_repo = user_repo

    async def create_workspace(self, user_id: int, data: WorkspaceCreate) -> Workspace:
        base_slug = slugify(data.name)
        slug = base_slug
        counter = 1
        while await self.ws_repo.get_by_slug(slug) is not None:
            slug = f"{base_slug}-{counter}"
            counter += 1

        workspace = Workspace(
            name=data.name,
            slug=slug,
            description=data.description,
            owner_id=user_id,
        )
        self.db.add(workspace)
        await self.db.flush()
        await self.db.refresh(workspace)

        # Creator automatically becomes OWNER member
        await self.member_repo.add_member(
            workspace_id=workspace.id,
            user_id=user_id,
            role=WorkspaceRole.OWNER,
        )

        await self.db.commit()
        await self.db.refresh(workspace)
        return workspace

    async def get_workspace_detail(self, workspace_id: int, user_id: int) -> Workspace:
        workspace = await self.ws_repo.get_by_id_with_details(workspace_id)
        if workspace is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found",
            )

        is_owner = workspace.owner_id == user_id
        is_member = any(m.user_id == user_id for m in workspace.members)
        if not (is_owner or is_member):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: Not a member of this workspace",
            )

        return workspace

    async def list_user_workspaces(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = DEFAULT_PAGE_SIZE,
    ) -> tuple[list[Workspace], int]:
        return await self.ws_repo.get_user_workspaces(user_id=user_id, skip=skip, limit=limit)

    async def update_workspace(
        self,
        workspace_id: int,
        user_id: int,
        data: WorkspaceUpdate,
    ) -> Workspace:
        workspace = await self.ws_repo.get(workspace_id)
        if workspace is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found",
            )

        # Permission check: OWNER or ADMIN
        is_owner = workspace.owner_id == user_id
        member = await self.member_repo.get_member(workspace_id, user_id)
        is_admin = member is not None and str(member.role).upper() in [
            WorkspaceRole.OWNER.value,
            WorkspaceRole.ADMIN.value,
        ]

        if not (is_owner or is_admin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied",
            )

        update_dict = data.model_dump(exclude_unset=True)
        if "name" in update_dict and update_dict["name"] is not None:
            workspace.name = update_dict["name"]
        if "description" in update_dict:
            workspace.description = update_dict["description"]

        self.db.add(workspace)
        await self.db.commit()
        await self.db.refresh(workspace)
        return workspace

    async def delete_workspace(self, workspace_id: int, user_id: int) -> None:
        workspace = await self.ws_repo.get(workspace_id)
        if workspace is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found",
            )

        if workspace.owner_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the workspace owner can delete this workspace",
            )

        await self.ws_repo.remove(workspace_id)
        await self.db.commit()

    async def add_member(
        self,
        workspace_id: int,
        current_user_id: int,
        data: WorkspaceMemberAdd,
    ) -> WorkspaceMember:
        workspace = await self.ws_repo.get(workspace_id)
        if workspace is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found",
            )

        # Permission check: current user must be OWNER or ADMIN
        is_owner = workspace.owner_id == current_user_id
        current_member = await self.member_repo.get_member(workspace_id, current_user_id)
        is_admin = current_member is not None and str(current_member.role).upper() in [
            WorkspaceRole.OWNER.value,
            WorkspaceRole.ADMIN.value,
        ]

        if not (is_owner or is_admin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied: Only OWNER or ADMIN can invite members",
            )

        # Target user lookup
        target_user = await self.user_repo.get_by_email(data.email)
        if target_user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User with this email not found",
            )

        # Check existing member
        existing_member = await self.member_repo.get_member(workspace_id, target_user.id)
        if existing_member is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User is already a member of this workspace",
            )

        new_member = await self.member_repo.add_member(
            workspace_id=workspace_id,
            user_id=target_user.id,
            role=data.role,
        )
        await self.db.commit()
        # Reload member with user relationship for response
        loaded_member = await self.member_repo.get_member(workspace_id, target_user.id)
        return loaded_member or new_member

    async def remove_member(
        self,
        workspace_id: int,
        current_user_id: int,
        target_user_id: int,
    ) -> None:
        workspace = await self.ws_repo.get(workspace_id)
        if workspace is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found",
            )

        if workspace.owner_id != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the workspace owner can remove members",
            )

        if target_user_id == workspace.owner_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove the workspace owner",
            )

        existing_member = await self.member_repo.get_member(workspace_id, target_user_id)
        if existing_member is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Member not found in this workspace",
            )

        await self.member_repo.remove_member(workspace_id, target_user_id)
        await self.db.commit()
