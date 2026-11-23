from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from taskhub.models.label import Label
from taskhub.models.task_label import TaskLabel
from taskhub.repositories.base import BaseRepository
from taskhub.schemas.label import LabelCreate, LabelUpdate


class LabelRepository(BaseRepository[Label, LabelCreate, LabelUpdate]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(model=Label, db=db)

    async def get_by_project(self, project_id: int) -> list[Label]:
        stmt = select(Label).where(Label.project_id == project_id).order_by(Label.id.asc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_project_paginated(
        self,
        project_id: int,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[Label], int]:
        count_stmt = select(func.count()).select_from(Label).where(Label.project_id == project_id)
        count_res = await self.db.execute(count_stmt)
        total = count_res.scalar() or 0

        stmt = (
            select(Label)
            .where(Label.project_id == project_id)
            .order_by(Label.id.asc())
            .offset(skip)
            .limit(limit)
        )
        res = await self.db.execute(stmt)
        items = list(res.scalars().all())
        return items, total

    async def get_by_project_and_name(self, project_id: int, name: str) -> Label | None:
        stmt = select(Label).where(
            Label.project_id == project_id,
            Label.name == name,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_task_label(self, task_id: int, label_id: int) -> TaskLabel | None:
        stmt = select(TaskLabel).where(
            TaskLabel.task_id == task_id,
            TaskLabel.label_id == label_id,
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def attach_to_task(self, task_id: int, label_id: int) -> TaskLabel:
        task_label = TaskLabel(task_id=task_id, label_id=label_id)
        self.db.add(task_label)
        await self.db.flush()
        return task_label

    async def detach_from_task(self, task_id: int, label_id: int) -> bool:
        stmt = select(TaskLabel).where(
            TaskLabel.task_id == task_id,
            TaskLabel.label_id == label_id,
        )
        res = await self.db.execute(stmt)
        task_label = res.scalar_one_or_none()
        if task_label is not None:
            await self.db.delete(task_label)
            await self.db.flush()
            return True
        return False

    async def is_attached(self, task_id: int, label_id: int) -> bool:
        stmt = select(TaskLabel).where(
            TaskLabel.task_id == task_id,
            TaskLabel.label_id == label_id,
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none() is not None

    async def get_task_labels(self, task_id: int) -> list[Label]:
        stmt = (
            select(Label)
            .join(TaskLabel, TaskLabel.label_id == Label.id)
            .where(TaskLabel.task_id == task_id)
            .order_by(Label.id.asc())
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())
