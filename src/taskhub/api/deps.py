from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from taskhub.db.session import get_db
from taskhub.repositories.task_repo import TaskRepository
from taskhub.services.task_service import TaskService


def get_task_repo(db: AsyncSession = Depends(get_db)) -> TaskRepository:
    return TaskRepository(db=db)


def get_task_service(
    repo: TaskRepository = Depends(get_task_repo),
) -> TaskService:
    return TaskService(task_repo=repo)
