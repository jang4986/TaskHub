from typing import Annotated

from fastapi import APIRouter, Path, Query, Response, status

from taskhub.api.deps import CurrentActiveUser, ProjectServ
from taskhub.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate

router = APIRouter()


# ---------------------------------------------------------
# Workspace - Projects Endpoints
# ---------------------------------------------------------
@router.post(
    "/workspaces/{workspace_id}/projects",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a project in a workspace",
)
async def create_project(
    project_in: ProjectCreate,
    current_user: CurrentActiveUser,
    service: ProjectServ,
    workspace_id: Annotated[int, Path(ge=1)],
) -> ProjectResponse:
    project = await service.create_project(
        workspace_id=workspace_id,
        user_id=current_user.id,
        data=project_in,
    )
    return ProjectResponse.model_validate(project)


@router.get(
    "/workspaces/{workspace_id}/projects",
    response_model=list[ProjectResponse],
    summary="List projects in a workspace",
)
async def list_workspace_projects(
    response: Response,
    current_user: CurrentActiveUser,
    service: ProjectServ,
    workspace_id: Annotated[int, Path(ge=1)],
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=100,
            description="Max number of items to return",
        ),
    ] = 20,
    skip: Annotated[int | None, Query(ge=0, description="Number of items to skip")] = None,
) -> list[ProjectResponse]:
    offset = skip if skip is not None else (page - 1) * limit
    projects, total = await service.list_projects(
        workspace_id=workspace_id,
        user_id=current_user.id,
        skip=offset,
        limit=limit,
    )
    response.headers["X-Total-Count"] = str(total)
    return [ProjectResponse.model_validate(p) for p in projects]


# ---------------------------------------------------------
# Individual Project Endpoints
# ---------------------------------------------------------
@router.get(
    "/projects/{project_id}",
    response_model=ProjectResponse,
    summary="Get project details by ID",
)
async def get_project(
    current_user: CurrentActiveUser,
    service: ProjectServ,
    project_id: Annotated[int, Path(ge=1)],
) -> ProjectResponse:
    project = await service.get_project(
        project_id=project_id,
        user_id=current_user.id,
    )
    return ProjectResponse.model_validate(project)


@router.patch(
    "/projects/{project_id}",
    response_model=ProjectResponse,
    summary="Update project details",
)
async def update_project(
    project_in: ProjectUpdate,
    current_user: CurrentActiveUser,
    service: ProjectServ,
    project_id: Annotated[int, Path(ge=1)],
) -> ProjectResponse:
    project = await service.update_project(
        project_id=project_id,
        user_id=current_user.id,
        data=project_in,
    )
    return ProjectResponse.model_validate(project)


@router.delete(
    "/projects/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a project",
)
async def delete_project(
    current_user: CurrentActiveUser,
    service: ProjectServ,
    project_id: Annotated[int, Path(ge=1)],
) -> None:
    await service.delete_project(
        project_id=project_id,
        user_id=current_user.id,
    )
