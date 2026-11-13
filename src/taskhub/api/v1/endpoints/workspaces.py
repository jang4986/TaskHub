from typing import Annotated

from fastapi import APIRouter, Path, Query, Response, status

from taskhub.api.deps import CurrentActiveUser, WorkspaceServ
from taskhub.core.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from taskhub.schemas.workspace import (
    WorkspaceCreate,
    WorkspaceDetailResponse,
    WorkspaceResponse,
    WorkspaceUpdate,
)
from taskhub.schemas.workspace_member import WorkspaceMemberAdd, WorkspaceMemberResponse

router = APIRouter()


@router.post(
    "",
    response_model=WorkspaceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new workspace",
)
async def create_workspace(
    data: WorkspaceCreate,
    current_user: CurrentActiveUser,
    workspace_service: WorkspaceServ,
) -> WorkspaceResponse:
    workspace = await workspace_service.create_workspace(user_id=current_user.id, data=data)
    return WorkspaceResponse.model_validate(workspace)


@router.get(
    "",
    response_model=list[WorkspaceResponse],
    summary="List workspaces for current user",
)
async def list_workspaces(
    response: Response,
    current_user: CurrentActiveUser,
    workspace_service: WorkspaceServ,
    skip: Annotated[int, Query(ge=0, description="Number of items to skip")] = 0,
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=MAX_PAGE_SIZE,
            description="Max number of items to return",
        ),
    ] = DEFAULT_PAGE_SIZE,
) -> list[WorkspaceResponse]:
    workspaces, total = await workspace_service.list_user_workspaces(
        user_id=current_user.id,
        skip=skip,
        limit=limit,
    )
    response.headers["X-Total-Count"] = str(total)
    return [WorkspaceResponse.model_validate(ws) for ws in workspaces]


@router.get(
    "/{workspace_id}",
    response_model=WorkspaceDetailResponse,
    summary="Get workspace details with members",
)
async def get_workspace(
    current_user: CurrentActiveUser,
    workspace_service: WorkspaceServ,
    workspace_id: Annotated[int, Path(ge=1)],
) -> WorkspaceDetailResponse:
    workspace = await workspace_service.get_workspace_detail(
        workspace_id=workspace_id,
        user_id=current_user.id,
    )
    return WorkspaceDetailResponse.model_validate(workspace)


@router.patch(
    "/{workspace_id}",
    response_model=WorkspaceResponse,
    summary="Update workspace details",
)
async def update_workspace(
    data: WorkspaceUpdate,
    current_user: CurrentActiveUser,
    workspace_service: WorkspaceServ,
    workspace_id: Annotated[int, Path(ge=1)],
) -> WorkspaceResponse:
    workspace = await workspace_service.update_workspace(
        workspace_id=workspace_id,
        user_id=current_user.id,
        data=data,
    )
    return WorkspaceResponse.model_validate(workspace)


@router.delete(
    "/{workspace_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a workspace (Owner only)",
)
async def delete_workspace(
    current_user: CurrentActiveUser,
    workspace_service: WorkspaceServ,
    workspace_id: Annotated[int, Path(ge=1)],
) -> None:
    await workspace_service.delete_workspace(
        workspace_id=workspace_id,
        user_id=current_user.id,
    )


@router.post(
    "/{workspace_id}/members",
    response_model=WorkspaceMemberResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a member to workspace",
)
async def add_workspace_member(
    data: WorkspaceMemberAdd,
    current_user: CurrentActiveUser,
    workspace_service: WorkspaceServ,
    workspace_id: Annotated[int, Path(ge=1)],
) -> WorkspaceMemberResponse:
    member = await workspace_service.add_member(
        workspace_id=workspace_id,
        current_user_id=current_user.id,
        data=data,
    )
    return WorkspaceMemberResponse.model_validate(member)


@router.delete(
    "/{workspace_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a member from workspace",
)
async def remove_workspace_member(
    current_user: CurrentActiveUser,
    workspace_service: WorkspaceServ,
    workspace_id: Annotated[int, Path(ge=1)],
    user_id: Annotated[int, Path(ge=1)],
) -> None:
    await workspace_service.remove_member(
        workspace_id=workspace_id,
        current_user_id=current_user.id,
        target_user_id=user_id,
    )
