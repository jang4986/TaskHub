from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from taskhub.models.workspace import Workspace
from taskhub.repositories.base import BaseRepository


class WorkspaceRepository(BaseRepository[Workspace, Any, Any]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(model=Workspace, db=db)

    async def get_by_owner(self, owner_id: int) -> list[Workspace]:
        stmt = select(Workspace).where(Workspace.owner_id == owner_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
