from typing import Optional, Union
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from taskhub.core.constants import DEFAULT_PAGE_SIZE
from taskhub.core.enums import TaskPriority, TaskStatus
from taskhub.models.task import Task
from taskhub.repositories.base import BaseRepository
from taskhub.schemas.task import TaskCreate, TaskUpdate


class TaskRepository(BaseRepository[Task, TaskCreate, TaskUpdate]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(model=Task, db=db)

    async def create_with_project(
        self,
        project_id: int,
        created_by: int,
        obj_in: TaskCreate,
    ) -> Task:
        task_data = obj_in.model_dump()
        task_data["project_id"] = project_id
        task_data["created_by"] = created_by
        return await self.create(task_data)

    async def get_by_project(
        self,
        project_id: int,
        skip: int = 0,
        limit: int = DEFAULT_PAGE_SIZE,
        status: Optional[Union[TaskStatus, str]] = None,
        priority: Optional[Union[TaskPriority, str]] = None,
    ) -> tuple[list[Task], int]:
        filters = [Task.project_id == project_id]

        if status is not None:
            status_val = status.value if hasattr(status, "value") else str(status)
            filters.append(Task.status == status_val)

        if priority is not None:
            priority_val = priority.value if hasattr(priority, "value") else str(priority)
            filters.append(Task.priority == priority_val)

        # Count total matching tasks
        total_stmt = select(func.count()).select_from(Task).where(*filters)
        total_res = await self.db.execute(total_stmt)
        total = total_res.scalar() or 0

        # Query paginated tasks with id tie-breaker
        stmt = (
            select(Task)
            .where(*filters)
            .order_by(Task.created_at.desc(), Task.id.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())

        return items, total
