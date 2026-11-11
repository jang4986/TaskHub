from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from taskhub.core.enums import WorkspaceRole
from taskhub.schemas.user import UserResponse


class WorkspaceMemberBase(BaseModel):
    role: WorkspaceRole = WorkspaceRole.MEMBER


class WorkspaceMemberAdd(BaseModel):
    email: EmailStr
    role: WorkspaceRole = WorkspaceRole.MEMBER


class WorkspaceMemberUpdate(BaseModel):
    role: WorkspaceRole


class WorkspaceMemberResponse(WorkspaceMemberBase):
    workspace_id: int
    user_id: int
    joined_at: datetime
    user: UserResponse | None = None

    model_config = ConfigDict(from_attributes=True)
