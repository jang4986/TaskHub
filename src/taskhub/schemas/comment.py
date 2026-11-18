from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from taskhub.schemas.user import UserResponse


class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1, description="Nội dung bình luận")

    @field_validator("content")
    @classmethod
    def strip_content(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Comment content cannot be empty or only whitespace")
        return v


class CommentResponse(BaseModel):
    id: int
    task_id: int
    author_id: int
    content: str
    created_at: datetime
    author: UserResponse | None = None

    model_config = ConfigDict(from_attributes=True)
