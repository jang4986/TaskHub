from datetime import datetime

from pydantic import BaseModel, ConfigDict

from taskhub.core.enums import NotificationType


class NotificationBase(BaseModel):
    title: str
    message: str
    type: str = NotificationType.TASK_ASSIGNED.value
    is_read: bool = False


class NotificationCreate(NotificationBase):
    user_id: int


class NotificationUpdate(BaseModel):
    is_read: bool | None = None


class NotificationResponse(BaseModel):
    id: int
    user_id: int
    type: str
    title: str
    message: str
    is_read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
