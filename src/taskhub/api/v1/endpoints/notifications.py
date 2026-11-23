from typing import Annotated

from fastapi import APIRouter, Path, Query, Response, status

from taskhub.api.deps import CurrentActiveUser, NotificationServ, Pagination
from taskhub.schemas.notification import NotificationResponse

router = APIRouter()


@router.get(
    "/notifications",
    response_model=list[NotificationResponse],
    summary="List current user notifications",
    description="Retrieves a paginated list of notifications for the authenticated user.",
    responses={
        status.HTTP_200_OK: {"description": "Notifications retrieved successfully"},
        status.HTTP_401_UNAUTHORIZED: {"description": "Authentication required"},
    },
)
async def list_notifications(
    response: Response,
    current_user: CurrentActiveUser,
    service: NotificationServ,
    pagination: Pagination,
    unread_only: Annotated[
        bool,
        Query(description="Filter only unread notifications"),
    ] = False,
) -> list[NotificationResponse]:
    notifications, total = await service.list_user_notifications(
        user_id=current_user.id,
        skip=pagination.offset,
        limit=pagination.limit,
        unread_only=unread_only,
    )
    response.headers["X-Total-Count"] = str(total)
    return [NotificationResponse.model_validate(n) for n in notifications]


@router.patch(
    "/notifications/{notification_id}/read",
    response_model=NotificationResponse,
    summary="Mark a notification as read",
    description="Marks the specified notification as read.",
    responses={
        status.HTTP_200_OK: {"description": "Notification marked as read"},
        status.HTTP_401_UNAUTHORIZED: {"description": "Authentication required"},
        status.HTTP_403_FORBIDDEN: {"description": "Cannot modify another user's notification"},
        status.HTTP_404_NOT_FOUND: {"description": "Notification not found"},
    },
)
async def mark_notification_read(
    notification_id: Annotated[int, Path(ge=1, description="Target Notification ID")],
    current_user: CurrentActiveUser,
    service: NotificationServ,
) -> NotificationResponse:
    notification = await service.mark_as_read(
        notification_id=notification_id,
        user_id=current_user.id,
    )
    return NotificationResponse.model_validate(notification)


@router.post(
    "/notifications/read-all",
    summary="Mark all unread notifications as read",
    description="Marks all unread notifications of the current user as read.",
    responses={
        status.HTTP_200_OK: {"description": "All notifications marked as read"},
        status.HTTP_401_UNAUTHORIZED: {"description": "Authentication required"},
    },
)
async def mark_all_notifications_read(
    current_user: CurrentActiveUser,
    service: NotificationServ,
) -> dict[str, int]:
    count = await service.mark_all_as_read(user_id=current_user.id)
    return {"updated_count": count}
