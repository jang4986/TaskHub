from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from taskhub.models.label import Label
from taskhub.repositories.base import BaseRepository


class LabelRepository(BaseRepository[Label, Any, Any]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(model=Label, db=db)

    async def get_by_project(self, project_id: int) -> list[Label]:
        stmt = select(Label).where(Label.project_id == project_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
