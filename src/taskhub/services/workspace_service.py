import re
import unicodedata
import uuid
from collections.abc import Collection

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from taskhub.core.constants import DEFAULT_PAGE_SIZE
from taskhub.core.enums import WorkspaceRole
from taskhub.core.exceptions import (
    CannotRemoveOwnerError,
    UserAlreadyWorkspaceMemberError,
    UserNotFoundError,
    WorkspaceAccessDeniedError,
    WorkspaceMemberNotFoundError,
    WorkspaceNotFoundError,
    WorkspaceSlugConflictError,
)
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


async def require_workspace_role(
    workspace_id: int,
    user_id: int,
    allowed_roles: Collection[WorkspaceRole | str] | None,
    ws_repo: WorkspaceRepository,
    member_repo: WorkspaceMemberRepository,
    denied_detail: str | None = None,
) -> tuple[Workspace, WorkspaceMember]:
    """Validate that workspace exists, user is a member, and role matches allowed_roles."""
    workspace = await ws_repo.get(workspace_id)
    if workspace is None:
        raise WorkspaceNotFoundError(workspace_id)

    member = await member_repo.get_member(workspace_id, user_id)
    if member is None:
        raise WorkspaceAccessDeniedError("Not a member of this workspace")

    if allowed_roles is not None:
        allowed_str = {r.value if hasattr(r, "value") else str(r) for r in allowed_roles}
        member_role_str = member.role.value if hasattr(member.role, "value") else str(member.role)
        if member_role_str not in allowed_str:
            detail = denied_detail or "Insufficient privileges in this workspace"
            raise WorkspaceAccessDeniedError(detail)

    return workspace, member


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

        for _ in range(5):
            try:
                workspace = Workspace(
                    name=data.name,
                    slug=slug,
                    description=data.description,
                    owner_id=user_id,
                )
                self.db.add(workspace)
                await self.db.flush()

                # Creator automatically becomes OWNER member
                await self.member_repo.add_member(
                    workspace_id=workspace.id,
                    user_id=user_id,
                    role=WorkspaceRole.OWNER,
                )

                await self.db.commit()
                await self.db.refresh(workspace)
                return workspace
            except IntegrityError:
                await self.db.rollback()
                slug = f"{base_slug}-{uuid.uuid4().hex[:6]}"

        raise WorkspaceSlugConflictError("Could not create workspace due to slug conflict")

    async def get_workspace_detail(self, workspace_id: int, user_id: int) -> Workspace:
        workspace = await self.ws_repo.get_by_id_with_details(workspace_id)
        if workspace is None:
            raise WorkspaceNotFoundError(workspace_id)

        is_member = any(m.user_id == user_id for m in workspace.members)
        if not is_member:
            raise WorkspaceAccessDeniedError("Access forbidden: Not a member of this workspace")

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
        workspace, _ = await require_workspace_role(
            workspace_id=workspace_id,
            user_id=user_id,
            allowed_roles={WorkspaceRole.OWNER, WorkspaceRole.ADMIN},
            ws_repo=self.ws_repo,
            member_repo=self.member_repo,
            denied_detail="Permission denied",
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
        await require_workspace_role(
            workspace_id=workspace_id,
            user_id=user_id,
            allowed_roles={WorkspaceRole.OWNER},
            ws_repo=self.ws_repo,
            member_repo=self.member_repo,
            denied_detail="Only the workspace owner can delete this workspace",
        )

        await self.ws_repo.remove(workspace_id)
        await self.db.commit()

    async def add_member(
        self,
        workspace_id: int,
        current_user_id: int,
        data: WorkspaceMemberAdd,
    ) -> WorkspaceMember:
        await require_workspace_role(
            workspace_id=workspace_id,
            user_id=current_user_id,
            allowed_roles={WorkspaceRole.OWNER, WorkspaceRole.ADMIN},
            ws_repo=self.ws_repo,
            member_repo=self.member_repo,
            denied_detail="Permission denied: Only OWNER or ADMIN can invite members",
        )

        target_user = await self.user_repo.get_by_email(data.email)
        if target_user is None:
            raise UserNotFoundError(detail="User with this email not found")

        existing_member = await self.member_repo.get_member(workspace_id, target_user.id)
        if existing_member is not None:
            raise UserAlreadyWorkspaceMemberError()

        try:
            new_member = await self.member_repo.add_member(
                workspace_id=workspace_id,
                user_id=target_user.id,
                role=data.role,
            )
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise UserAlreadyWorkspaceMemberError() from None

        loaded_member = await self.member_repo.get_member(workspace_id, target_user.id)
        return loaded_member or new_member

    async def remove_member(
        self,
        workspace_id: int,
        current_user_id: int,
        target_user_id: int,
    ) -> None:
        workspace, _ = await require_workspace_role(
            workspace_id=workspace_id,
            user_id=current_user_id,
            allowed_roles={WorkspaceRole.OWNER},
            ws_repo=self.ws_repo,
            member_repo=self.member_repo,
            denied_detail="Only the workspace owner can remove members",
        )

        if target_user_id == workspace.owner_id:
            raise CannotRemoveOwnerError()

        existing_member = await self.member_repo.get_member(workspace_id, target_user_id)
        if existing_member is None:
            raise WorkspaceMemberNotFoundError(target_user_id)

        await self.member_repo.remove_member(workspace_id, target_user_id)
        await self.db.commit()
