from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from taskhub.core.constants import DEFAULT_PAGE_SIZE
from taskhub.models.comment import Comment
from taskhub.repositories.base import BaseRepository
from taskhub.schemas.comment import CommentCreate


class CommentRepository(BaseRepository[Comment, CommentCreate, CommentCreate]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(model=Comment, db=db)

    async def get_by_task(self, task_id: int) -> list[Comment]:
        stmt = (
            select(Comment)
            .where(Comment.task_id == task_id)
            .options(selectinload(Comment.author))
            .order_by(Comment.created_at.asc(), Comment.id.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_task_paginated(
        self,
        task_id: int,
        skip: int = 0,
        limit: int = DEFAULT_PAGE_SIZE,
    ) -> tuple[list[Comment], int]:
        count_stmt = select(func.count()).select_from(Comment).where(Comment.task_id == task_id)
        count_res = await self.db.execute(count_stmt)
        total = count_res.scalar() or 0

        stmt = (
            select(Comment)
            .where(Comment.task_id == task_id)
            .options(selectinload(Comment.author))
            .order_by(Comment.created_at.asc(), Comment.id.asc())
            .offset(skip)
            .limit(limit)
        )
        res = await self.db.execute(stmt)
        items = list(res.scalars().all())
        return items, total

    async def get_with_author(self, comment_id: int) -> Comment | None:
        stmt = select(Comment).where(Comment.id == comment_id).options(selectinload(Comment.author))
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()
