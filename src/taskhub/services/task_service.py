from enum import Enum
from typing import Any, Optional, Union
from fastapi import HTTPException, status

from taskhub.repositories.task_repo import TaskRepository
from taskhub.schemas.task import TaskCreate, TaskPriority, TaskStatus, TaskUpdate


class TaskService:
    def __init__(self, task_repo: TaskRepository) -> None:
        self.task_repo = task_repo

    def create_task(self, project_id: int, task_in: TaskCreate) -> dict[str, Any]:
        task_data = task_in.model_dump()
        return self.task_repo.create(project_id=project_id, task_data=task_data)

    def get_task(self, task_id: int) -> dict[str, Any]:
        task = self.task_repo.get_by_id(task_id)
        if task is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task with id {task_id} not found",
            )
        return task

    def get_project_tasks(
        self,
        project_id: int,
        skip: int = 0,
        limit: int = 20,
        status_filter: Optional[Union[TaskStatus, str]] = None,
        priority_filter: Optional[Union[TaskPriority, str]] = None,
    ) -> list[dict[str, Any]]:
        status_val: Optional[str] = None
        if isinstance(status_filter, Enum):
            status_val = status_filter.value
        elif isinstance(status_filter, str):
            status_val = status_filter

        priority_val: Optional[str] = None
        if isinstance(priority_filter, Enum):
            priority_val = priority_filter.value
        elif isinstance(priority_filter, str):
            priority_val = priority_filter

        return self.task_repo.get_by_project(
            project_id=project_id,
            skip=skip,
            limit=limit,
            status=status_val,
            priority=priority_val,
        )

    def update_task(self, task_id: int, task_in: TaskUpdate) -> dict[str, Any]:
        # Validate task existence first
        self.get_task(task_id)

        update_data = task_in.model_dump(exclude_unset=True)
        updated_task = self.task_repo.update(task_id=task_id, update_data=update_data)
        if updated_task is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task with id {task_id} not found",
            )
        return updated_task

    def delete_task(self, task_id: int) -> None:
        deleted = self.task_repo.delete(task_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task with id {task_id} not found",
            )
