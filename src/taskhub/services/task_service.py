from typing import Optional, Union
from fastapi import HTTPException, status

from taskhub.models.task import Task
from taskhub.repositories.task_repo import TaskRepository
from taskhub.schemas.task import TaskCreate, TaskPriority, TaskStatus, TaskUpdate


class TaskService:
    def __init__(self, task_repo: TaskRepository) -> None:
        self.task_repo = task_repo

    async def create_task(self, project_id: int, task_in: TaskCreate) -> Task:
        return await self.task_repo.create_with_project(project_id=project_id, obj_in=task_in)

    async def get_task(self, task_id: int) -> Task:
        task = await self.task_repo.get(task_id)
        if task is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task with id {task_id} not found",
            )
        return task

    async def get_project_tasks(
        self,
        project_id: int,
        skip: int = 0,
        limit: int = 20,
        status_filter: Optional[Union[TaskStatus, str]] = None,
        priority_filter: Optional[Union[TaskPriority, str]] = None,
    ) -> list[Task]:
        return await self.task_repo.get_by_project(
            project_id=project_id,
            skip=skip,
            limit=limit,
            status=status_filter,
            priority=priority_filter,
        )

    async def update_task(self, task_id: int, task_in: TaskUpdate) -> Task:
        task = await self.get_task(task_id)
        return await self.task_repo.update(db_obj=task, obj_in=task_in)

    async def delete_task(self, task_id: int) -> None:
        task = await self.get_task(task_id)
        await self.task_repo.remove(id=task.id)
