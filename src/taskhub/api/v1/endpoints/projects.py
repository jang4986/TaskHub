from typing import Annotated

from fastapi import APIRouter, Path, Query, Response, status

from taskhub.api.deps import CurrentActiveUser, ProjectServ, TaskServ
from taskhub.core.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from taskhub.core.enums import TaskPriority, TaskStatus
from taskhub.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate
from taskhub.schemas.task import TaskCreate, TaskResponse

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
    skip: Annotated[int, Query(ge=0, description="Number of items to skip")] = 0,
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=MAX_PAGE_SIZE,
            description="Max number of items to return",
        ),
    ] = DEFAULT_PAGE_SIZE,
) -> list[ProjectResponse]:
    projects, total = await service.list_projects(
        workspace_id=workspace_id,
        user_id=current_user.id,
        skip=skip,
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


# ---------------------------------------------------------
# Project - Tasks Endpoints (Preserved for full compatibility)
# ---------------------------------------------------------
@router.post(
    "/projects/{project_id}/tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a task for a project",
)
async def create_task_for_project(
    project_id: Annotated[int, Path(ge=1)],
    task_in: TaskCreate,
    current_user: CurrentActiveUser,
    service: TaskServ,
) -> TaskResponse:
    task = await service.create_task(
        project_id=project_id,
        created_by=current_user.id,
        task_in=task_in,
        current_user=current_user,
    )
    return TaskResponse.model_validate(task)


@router.get(
    "/projects/{project_id}/tasks",
    response_model=list[TaskResponse],
    summary="List tasks of a project with pagination and filters",
)
async def list_tasks_for_project(
    project_id: Annotated[int, Path(ge=1)],
    response: Response,
    current_user: CurrentActiveUser,
    service: TaskServ,
    skip: Annotated[int, Query(ge=0, description="Number of items to skip")] = 0,
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=MAX_PAGE_SIZE,
            description="Max number of items to return",
        ),
    ] = DEFAULT_PAGE_SIZE,
    status: Annotated[TaskStatus | None, Query(description="Filter by status")] = None,
    priority: Annotated[TaskPriority | None, Query(description="Filter by priority")] = None,
) -> list[TaskResponse]:
    tasks, total = await service.get_project_tasks(
        project_id=project_id,
        current_user=current_user,
        skip=skip,
        limit=limit,
        status_filter=status,
        priority_filter=priority,
    )
    response.headers["X-Total-Count"] = str(total)
    return [TaskResponse.model_validate(t) for t in tasks]
