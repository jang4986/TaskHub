from fastapi import Depends

from taskhub.repositories.task_repo import TaskRepository
from taskhub.services.task_service import TaskService

_task_repo_instance = TaskRepository()


def get_task_repo() -> TaskRepository:
    return _task_repo_instance


def get_task_service(
    repo: TaskRepository = Depends(get_task_repo),
) -> TaskService:
    return TaskService(task_repo=repo)
