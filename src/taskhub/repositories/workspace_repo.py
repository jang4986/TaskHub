from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from taskhub.core.constants import DEFAULT_PAGE_SIZE
from taskhub.models.workspace import Workspace
from taskhub.models.workspace_member import WorkspaceMember
from taskhub.repositories.base import BaseRepository


class WorkspaceRepository(BaseRepository[Workspace, Any, Any]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(model=Workspace, db=db)

    async def get_by_owner(self, owner_id: int) -> list[Workspace]:
        stmt = select(Workspace).where(Workspace.owner_id == owner_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_slug(self, slug: str) -> Workspace | None:
        stmt = select(Workspace).where(Workspace.slug == slug)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_user_workspaces(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = DEFAULT_PAGE_SIZE,
    ) -> tuple[list[Workspace], int]:
        member_subquery = (
            select(WorkspaceMember.workspace_id)
            .where(WorkspaceMember.user_id == user_id)
            .scalar_subquery()
        )
        condition = or_(
            Workspace.owner_id == user_id,
            Workspace.id.in_(member_subquery),
        )

        count_stmt = select(func.count()).select_from(Workspace).where(condition)
        count_res = await self.db.execute(count_stmt)
        total = count_res.scalar() or 0

        stmt = (
            select(Workspace)
            .where(condition)
            .order_by(Workspace.id.asc())
            .offset(skip)
            .limit(limit)
        )
        res = await self.db.execute(stmt)
        items = list(res.scalars().all())
        return items, total

    async def get_by_id_with_details(self, workspace_id: int) -> Workspace | None:
        stmt = (
            select(Workspace)
            .where(Workspace.id == workspace_id)
            .options(
                selectinload(Workspace.members).selectinload(WorkspaceMember.user),
                selectinload(Workspace.projects),
            )
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()
