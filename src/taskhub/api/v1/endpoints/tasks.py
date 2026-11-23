from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Path, Query, Response, status

from taskhub.api.deps import CurrentActiveUser, Pagination, TaskServ
from taskhub.core.enums import TaskPriority, TaskStatus
from taskhub.schemas.task import TaskCreate, TaskResponse, TaskUpdate

router = APIRouter()


# ---------------------------------------------------------
# Project - Tasks Endpoints
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
    background_tasks: BackgroundTasks,
) -> TaskResponse:
    task = await service.create_task(
        project_id=project_id,
        created_by=current_user.id,
        task_in=task_in,
        current_user=current_user,
        background_tasks=background_tasks,
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
    pagination: Pagination,
    status: Annotated[TaskStatus | None, Query(description="Filter by status")] = None,
    priority: Annotated[TaskPriority | None, Query(description="Filter by priority")] = None,
    assignee_id: Annotated[int | None, Query(description="Filter by assignee")] = None,
) -> list[TaskResponse]:
    tasks, total, is_cache_hit = await service.get_project_tasks(
        project_id=project_id,
        current_user=current_user,
        skip=pagination.offset,
        limit=pagination.limit,
        status_filter=status,
        priority_filter=priority,
        assignee_id_filter=assignee_id,
    )
    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Cache"] = "HIT" if is_cache_hit else "MISS"
    return [TaskResponse.model_validate(t) for t in tasks]


# ---------------------------------------------------------
# Individual Task Endpoints
# ---------------------------------------------------------
@router.get(
    "/tasks/{task_id}",
    response_model=TaskResponse,
    summary="Get task details by ID",
)
async def get_task(
    task_id: Annotated[int, Path(ge=1)],
    current_user: CurrentActiveUser,
    service: TaskServ,
) -> TaskResponse:
    task = await service.get_task(task_id=task_id, current_user=current_user)
    return TaskResponse.model_validate(task)


@router.patch(
    "/tasks/{task_id}",
    response_model=TaskResponse,
    summary="Partially update a task",
)
async def update_task(
    task_id: Annotated[int, Path(ge=1)],
    task_in: TaskUpdate,
    current_user: CurrentActiveUser,
    service: TaskServ,
    background_tasks: BackgroundTasks,
) -> TaskResponse:
    task = await service.update_task(
        task_id=task_id,
        task_in=task_in,
        current_user=current_user,
        background_tasks=background_tasks,
    )
    return TaskResponse.model_validate(task)


@router.delete(
    "/tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a task by ID",
)
async def delete_task(
    task_id: Annotated[int, Path(ge=1)],
    current_user: CurrentActiveUser,
    service: TaskServ,
) -> Response:
    await service.delete_task(task_id=task_id, current_user=current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
