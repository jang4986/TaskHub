import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from taskhub.core.constants import DEFAULT_PAGE_SIZE
from taskhub.core.enums import NotificationType
from taskhub.core.exceptions import (
    NotificationAccessDeniedError,
    NotificationNotFoundError,
)
from taskhub.db.session import AsyncSessionLocal
from taskhub.models.notification import Notification
from taskhub.models.user import User
from taskhub.repositories.notification_repo import NotificationRepository

logger = logging.getLogger("taskhub.notifications")

# Module-level default session factory, overridable in tests
_session_factory: async_sessionmaker[AsyncSession] = AsyncSessionLocal


def set_notification_session_factory(factory: async_sessionmaker[AsyncSession]) -> None:
    """Set the session factory used by background task workers (e.g. for testing)."""
    global _session_factory
    _session_factory = factory


def get_notification_session_factory() -> async_sessionmaker[AsyncSession]:
    """Retrieve the current session factory for background workers."""
    return _session_factory


async def send_task_assigned_notification(
    assignee_id: int,
    task_id: int,
    task_title: str,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> None:
    """Background worker task to record DB notification and simulate email dispatch."""
    factory = session_factory or get_notification_session_factory()
    try:
        async with factory() as session:
            user = await session.get(User, assignee_id)
            if user is None:
                logger.warning(
                    "Assignee with id %s not found for task assignment notification",
                    assignee_id,
                )
                return

            notification = Notification(
                user_id=assignee_id,
                type=NotificationType.TASK_ASSIGNED.value,
                title="New Task Assigned",
                message=f"You have been assigned to task: {task_title}",
                is_read=False,
            )
            session.add(notification)
            await session.commit()

            logger.info(
                "[EMAIL NOTIFICATION] To: %s | Subject: New Task Assigned | Task #%s: %s",
                user.email,
                task_id,
                task_title,
            )
    except Exception as e:
        logger.error(
            "Failed to send task assignment notification to user %s for task %s: %s",
            assignee_id,
            task_id,
            e,
        )


class NotificationService:
    def __init__(
        self,
        db: AsyncSession,
        notification_repo: NotificationRepository,
    ) -> None:
        self.db = db
        self.notification_repo = notification_repo

    async def list_user_notifications(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = DEFAULT_PAGE_SIZE,
        unread_only: bool = False,
    ) -> tuple[list[Notification], int]:
        return await self.notification_repo.get_by_user_paginated(
            user_id=user_id,
            skip=skip,
            limit=limit,
            unread_only=unread_only,
        )

    async def mark_as_read(
        self,
        notification_id: int,
        user_id: int,
    ) -> Notification:
        notification = await self.notification_repo.get(notification_id)
        if notification is None:
            raise NotificationNotFoundError(notification_id)

        if notification.user_id != user_id:
            raise NotificationAccessDeniedError(
                "Access forbidden: You cannot modify notifications belonging to other users"
            )

        notification.is_read = True
        self.db.add(notification)
        await self.db.commit()
        await self.db.refresh(notification)
        return notification

    async def mark_all_as_read(self, user_id: int) -> int:
        count = await self.notification_repo.mark_all_as_read(user_id)
        await self.db.commit()
        return count
