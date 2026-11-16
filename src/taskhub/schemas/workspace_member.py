from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr

from taskhub.core.enums import WorkspaceRole
from taskhub.schemas.user import UserResponse

InvitableWorkspaceRole = Literal[
    WorkspaceRole.ADMIN,
    WorkspaceRole.MEMBER,
    WorkspaceRole.VIEWER,
]


class WorkspaceMemberBase(BaseModel):
    role: WorkspaceRole = WorkspaceRole.MEMBER


class WorkspaceMemberAdd(BaseModel):
    email: EmailStr
    role: InvitableWorkspaceRole = WorkspaceRole.MEMBER


class WorkspaceMemberUpdate(BaseModel):
    role: InvitableWorkspaceRole


class WorkspaceMemberResponse(WorkspaceMemberBase):
    workspace_id: int
    user_id: int
    joined_at: datetime
    user: UserResponse | None = None

    model_config = ConfigDict(from_attributes=True)
