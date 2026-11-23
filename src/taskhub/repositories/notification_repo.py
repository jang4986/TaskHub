from typing import Any, cast

from sqlalchemy import func, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from taskhub.models.notification import Notification
from taskhub.repositories.base import BaseRepository
from taskhub.schemas.notification import NotificationCreate, NotificationUpdate


class NotificationRepository(BaseRepository[Notification, NotificationCreate, NotificationUpdate]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(model=Notification, db=db)

    async def get_by_user_paginated(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 20,
        unread_only: bool = False,
    ) -> tuple[list[Notification], int]:
        count_stmt = (
            select(func.count()).select_from(Notification).where(Notification.user_id == user_id)
        )
        stmt = select(Notification).where(Notification.user_id == user_id)

        if unread_only:
            count_stmt = count_stmt.where(Notification.is_read.is_(False))
            stmt = stmt.where(Notification.is_read.is_(False))

        count_res = await self.db.execute(count_stmt)
        total = count_res.scalar() or 0

        stmt = (
            stmt.order_by(Notification.created_at.desc(), Notification.id.desc())
            .offset(skip)
            .limit(limit)
        )
        res = await self.db.execute(stmt)
        items = list(res.scalars().all())
        return items, total

    async def mark_all_as_read(self, user_id: int) -> int:
        stmt = (
            update(Notification)
            .where(Notification.user_id == user_id, Notification.is_read.is_(False))
            .values(is_read=True)
        )
        result = await self.db.execute(stmt)
        cursor_result = cast(CursorResult[Any], result)
        await self.db.flush()
        return cursor_result.rowcount or 0
