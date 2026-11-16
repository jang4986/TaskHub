
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from taskhub.core.constants import DEFAULT_PAGE_SIZE
from taskhub.core.enums import WorkspaceRole
from taskhub.models.workspace_member import WorkspaceMember


class WorkspaceMemberRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_member(self, workspace_id: int, user_id: int) -> WorkspaceMember | None:
        stmt = (
            select(WorkspaceMember)
            .where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user_id,
            )
            .options(selectinload(WorkspaceMember.user))
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def add_member(
        self,
        workspace_id: int,
        user_id: int,
        role: WorkspaceRole,
    ) -> WorkspaceMember:
        role_str = role.value if hasattr(role, "value") else str(role)
        member = WorkspaceMember(
            workspace_id=workspace_id,
            user_id=user_id,
            role=role_str,
        )
        self.db.add(member)
        await self.db.flush()
        # Refresh and ensure relationship user is loaded
        loaded_stmt = (
            select(WorkspaceMember)
            .where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user_id,
            )
            .options(selectinload(WorkspaceMember.user))
        )
        res = await self.db.execute(loaded_stmt)
        return res.scalar_one()

    async def update_role(
        self,
        workspace_id: int,
        user_id: int,
        role: WorkspaceRole,
    ) -> WorkspaceMember | None:
        member = await self.get_member(workspace_id=workspace_id, user_id=user_id)
        if member is None:
            return None
        role_str = role.value if hasattr(role, "value") else str(role)
        member.role = role_str
        self.db.add(member)
        await self.db.flush()
        return member

    async def remove_member(self, workspace_id: int, user_id: int) -> bool:
        stmt = select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
        res = await self.db.execute(stmt)
        member = res.scalar_one_or_none()
        if member is not None:
            await self.db.delete(member)
            await self.db.flush()
            return True
        return False

    async def list_members_by_workspace(
        self,
        workspace_id: int,
        skip: int = 0,
        limit: int = DEFAULT_PAGE_SIZE,
    ) -> tuple[list[WorkspaceMember], int]:
        count_stmt = (
            select(func.count())
            .select_from(WorkspaceMember)
            .where(WorkspaceMember.workspace_id == workspace_id)
        )
        count_res = await self.db.execute(count_stmt)
        total = count_res.scalar() or 0

        stmt = (
            select(WorkspaceMember)
            .where(WorkspaceMember.workspace_id == workspace_id)
            .options(selectinload(WorkspaceMember.user))
            .order_by(WorkspaceMember.created_at.asc(), WorkspaceMember.user_id.asc())
            .offset(skip)
            .limit(limit)
        )
        res = await self.db.execute(stmt)
        members = list(res.scalars().all())
        return members, total
