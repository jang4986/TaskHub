from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from taskhub.models.project import Project
from taskhub.repositories.base import BaseRepository


class ProjectRepository(BaseRepository[Project, Any, Any]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(model=Project, db=db)

    async def get_by_workspace(self, workspace_id: int) -> list[Project]:
        stmt = select(Project).where(Project.workspace_id == workspace_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
