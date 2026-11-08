from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class TaskStatus(str, Enum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    IN_REVIEW = "IN_REVIEW"
    DONE = "DONE"


class TaskPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"


class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="Tiêu đề công việc")
    description: Optional[str] = Field(None, description="Mô tả chi tiết công việc")
    status: TaskStatus = Field(default=TaskStatus.TODO, description="Trạng thái công việc")
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM, description="Mức độ ưu tiên")
    due_date: Optional[datetime] = Field(None, description="Hạn hoàn thành công việc")
    assignee_id: Optional[int] = Field(None, description="ID của người được phân công")


class TaskCreate(TaskBase):
    created_by: Optional[int] = Field(default=1, description="ID của người tạo task")


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255, description="Tiêu đề công việc")
    description: Optional[str] = Field(None, description="Mô tả chi tiết công việc")
    status: Optional[TaskStatus] = Field(None, description="Trạng thái công việc")
    priority: Optional[TaskPriority] = Field(None, description="Mức độ ưu tiên")
    due_date: Optional[datetime] = Field(None, description="Hạn hoàn thành công việc")
    assignee_id: Optional[int] = Field(None, description="ID của người được phân công")


class TaskResponse(TaskBase):
    id: int
    project_id: int
    created_by: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
