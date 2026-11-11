from typing import Optional
from fastapi import APIRouter, Query, Response, status

from taskhub.api.deps import CurrentActiveUser, TaskServ
from taskhub.core.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from taskhub.core.enums import TaskPriority, TaskStatus
from taskhub.schemas.task import TaskCreate, TaskResponse

router = APIRouter()


@router.post(
    "/projects/{project_id}/tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a task for a project",
)
async def create_task_for_project(
    project_id: int,
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
    project_id: int,
    response: Response,
    current_user: CurrentActiveUser,
    service: TaskServ,
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(
        DEFAULT_PAGE_SIZE,
        ge=1,
        le=MAX_PAGE_SIZE,
        description="Max number of items to return",
    ),
    status: Optional[TaskStatus] = Query(None, description="Filter by status"),
    priority: Optional[TaskPriority] = Query(None, description="Filter by priority"),
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
