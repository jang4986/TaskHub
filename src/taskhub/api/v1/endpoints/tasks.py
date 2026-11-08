from fastapi import APIRouter, Depends, Response, status

from taskhub.api.deps import get_task_service
from taskhub.schemas.task import TaskResponse, TaskUpdate
from taskhub.services.task_service import TaskService

router = APIRouter()


@router.get(
    "/tasks/{task_id}",
    response_model=TaskResponse,
    summary="Get task details by ID",
)
async def get_task(
    task_id: int,
    service: TaskService = Depends(get_task_service),
) -> TaskResponse:
    task = await service.get_task(task_id=task_id)
    return TaskResponse.model_validate(task)


@router.patch(
    "/tasks/{task_id}",
    response_model=TaskResponse,
    summary="Partially update a task",
)
async def update_task(
    task_id: int,
    task_in: TaskUpdate,
    service: TaskService = Depends(get_task_service),
) -> TaskResponse:
    task = await service.update_task(task_id=task_id, task_in=task_in)
    return TaskResponse.model_validate(task)


@router.delete(
    "/tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a task by ID",
)
async def delete_task(
    task_id: int,
    service: TaskService = Depends(get_task_service),
) -> Response:
    await service.delete_task(task_id=task_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
