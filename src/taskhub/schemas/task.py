from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from taskhub.core.enums import TaskPriority, TaskStatus


class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="Tiêu đề công việc")
    description: str | None = Field(None, description="Mô tả chi tiết công việc")
    status: TaskStatus = Field(default=TaskStatus.TODO, description="Trạng thái công việc")
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM, description="Mức độ ưu tiên")
    due_date: datetime | None = Field(None, description="Hạn hoàn thành công việc")
    assignee_id: int | None = Field(None, description="ID của người được phân công")


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255, description="Tiêu đề công việc")
    description: str | None = Field(None, description="Mô tả chi tiết công việc")
    status: TaskStatus | None = Field(None, description="Trạng thái công việc")
    priority: TaskPriority | None = Field(None, description="Mức độ ưu tiên")
    due_date: datetime | None = Field(None, description="Hạn hoàn thành công việc")
    assignee_id: int | None = Field(None, description="ID của người được phân công")


class TaskResponse(TaskBase):
    id: int
    project_id: int
    created_by: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


__all__ = [
    "TaskBase",
    "TaskCreate",
    "TaskPriority",
    "TaskResponse",
    "TaskStatus",
    "TaskUpdate",
]
