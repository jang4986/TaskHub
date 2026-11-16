from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from taskhub.models.comment import Comment
from taskhub.repositories.base import BaseRepository


class CommentRepository(BaseRepository[Comment, Any, Any]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(model=Comment, db=db)

    async def get_by_task(self, task_id: int) -> list[Comment]:
        stmt = select(Comment).where(Comment.task_id == task_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
