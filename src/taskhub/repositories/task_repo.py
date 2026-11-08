from typing import Optional, Union
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from taskhub.models.task import Task
from taskhub.repositories.base import BaseRepository
from taskhub.schemas.task import TaskCreate, TaskPriority, TaskStatus, TaskUpdate


class TaskRepository(BaseRepository[Task, TaskCreate, TaskUpdate]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(model=Task, db=db)

    async def create_with_project(self, project_id: int, obj_in: TaskCreate) -> Task:
        task_data = obj_in.model_dump()
        task_data["project_id"] = project_id
        if "status" in task_data and hasattr(task_data["status"], "value"):
            task_data["status"] = task_data["status"].value
        if "priority" in task_data and hasattr(task_data["priority"], "value"):
            task_data["priority"] = task_data["priority"].value
        return await self.create(task_data)

    async def get_by_project(
        self,
        project_id: int,
        skip: int = 0,
        limit: int = 20,
        status: Optional[Union[TaskStatus, str]] = None,
        priority: Optional[Union[TaskPriority, str]] = None,
    ) -> list[Task]:
        stmt = select(Task).where(Task.project_id == project_id)

        if status is not None:
            status_val = status.value if hasattr(status, "value") else str(status)
            stmt = stmt.where(Task.status == status_val)

        if priority is not None:
            priority_val = priority.value if hasattr(priority, "value") else str(priority)
            stmt = stmt.where(Task.priority == priority_val)

        stmt = stmt.offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
