from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from taskhub.core.enums import ProjectStatus
from taskhub.models.project import Project
from taskhub.repositories.base import BaseRepository
from taskhub.schemas.project import ProjectCreate, ProjectUpdate


class ProjectRepository(BaseRepository[Project, ProjectCreate, ProjectUpdate]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(model=Project, db=db)

    async def get_by_workspace(self, workspace_id: int) -> list[Project]:
        stmt = select(Project).where(Project.workspace_id == workspace_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_workspace_paginated(
        self,
        workspace_id: int,
        skip: int = 0,
        limit: int = 50,
        include_archived: bool = True,
    ) -> tuple[list[Project], int]:
        count_stmt = (
            select(func.count()).select_from(Project).where(Project.workspace_id == workspace_id)
        )
        stmt = select(Project).where(Project.workspace_id == workspace_id)

        if not include_archived:
            count_stmt = count_stmt.where(Project.status != ProjectStatus.ARCHIVED.value)
            stmt = stmt.where(Project.status != ProjectStatus.ARCHIVED.value)

        count_res = await self.db.execute(count_stmt)
        total = count_res.scalar() or 0

        stmt = (
            stmt.order_by(Project.created_at.desc(), Project.id.desc())
            .offset(skip)
            .limit(limit)
        )
        res = await self.db.execute(stmt)
        items = list(res.scalars().all())
        return items, total

    async def get_with_workspace(self, project_id: int) -> Project | None:
        stmt = (
            select(Project).where(Project.id == project_id).options(selectinload(Project.workspace))
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()
