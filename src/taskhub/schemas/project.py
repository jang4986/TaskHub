from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None


class ProjectResponse(BaseModel):
    id: int
    workspace_id: int | None = None
    name: str
    description: str | None = None
    owner_id: int | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
