from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from taskhub.schemas.workspace_member import WorkspaceMemberResponse


class WorkspaceBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: str | None = None


class WorkspaceCreate(WorkspaceBase):
    pass


class WorkspaceUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=100)
    description: str | None = None


class WorkspaceResponse(WorkspaceBase):
    id: int
    slug: str | None = None
    owner_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkspaceDetailResponse(WorkspaceResponse):
    members: list[WorkspaceMemberResponse] = []
