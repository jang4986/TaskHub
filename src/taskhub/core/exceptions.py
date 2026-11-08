"""Custom exceptions for TaskHub."""
from fastapi import HTTPException, status


class TaskNotFoundError(HTTPException):
    def __init__(self, task_id: int):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id {task_id} not found",
        )
