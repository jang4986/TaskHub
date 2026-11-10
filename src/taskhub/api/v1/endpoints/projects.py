from typing import Optional
from fastapi import APIRouter, Depends, Query, status

from taskhub.api.deps import get_current_active_user, get_task_service
from taskhub.models.user import User
from taskhub.schemas.task import TaskCreate, TaskPriority, TaskResponse, TaskStatus
from taskhub.services.task_service import TaskService

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
    current_user: User = Depends(get_current_active_user),
    service: TaskService = Depends(get_task_service),
) -> TaskResponse:
    task_in.created_by = current_user.id
    task = await service.create_task(project_id=project_id, task_in=task_in)
    return TaskResponse.model_validate(task)


@router.get(
    "/projects/{project_id}/tasks",
    response_model=list[TaskResponse],
    summary="List tasks of a project with pagination and filters",
)
async def list_tasks_for_project(
    project_id: int,
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(20, ge=1, le=100, description="Max number of items to return"),
    status: Optional[TaskStatus] = Query(None, description="Filter by status"),
    priority: Optional[TaskPriority] = Query(None, description="Filter by priority"),
    current_user: User = Depends(get_current_active_user),
    service: TaskService = Depends(get_task_service),
) -> list[TaskResponse]:
    tasks = await service.get_project_tasks(
        project_id=project_id,
        skip=skip,
        limit=limit,
        status_filter=status,
        priority_filter=priority,
    )
    return [TaskResponse.model_validate(t) for t in tasks]
