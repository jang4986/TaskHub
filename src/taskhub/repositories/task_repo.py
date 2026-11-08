from datetime import datetime, timezone
from typing import Any, Optional

fake_tasks_db: dict[int, dict[str, Any]] = {}


class TaskRepository:
    def __init__(self, db: Optional[dict[int, dict[str, Any]]] = None) -> None:
        self.db = db if db is not None else fake_tasks_db
        self._id_counter = max(self.db.keys(), default=0)

    def _next_id(self) -> int:
        self._id_counter += 1
        return self._id_counter

    def create(self, project_id: int, task_data: dict[str, Any]) -> dict[str, Any]:
        task_id = self._next_id()
        task = {
            "id": task_id,
            "project_id": project_id,
            **task_data,
            "created_at": datetime.now(timezone.utc),
        }
        self.db[task_id] = task
        return task.copy()

    def get_by_id(self, task_id: int) -> Optional[dict[str, Any]]:
        task = self.db.get(task_id)
        return task.copy() if task is not None else None

    def get_by_project(
        self,
        project_id: int,
        skip: int = 0,
        limit: int = 20,
        status: Optional[str] = None,
        priority: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for task in self.db.values():
            if task.get("project_id") != project_id:
                continue
            if status is not None:
                task_status = task.get("status")
                # Support both enum and string comparison
                current_status = getattr(task_status, "value", task_status)
                filter_status = getattr(status, "value", status)
                if current_status != filter_status:
                    continue
            if priority is not None:
                task_priority = task.get("priority")
                current_priority = getattr(task_priority, "value", task_priority)
                filter_priority = getattr(priority, "value", priority)
                if current_priority != filter_priority:
                    continue
            results.append(task.copy())

        return results[skip : skip + limit]

    def update(self, task_id: int, update_data: dict[str, Any]) -> Optional[dict[str, Any]]:
        if task_id not in self.db:
            return None
        task = self.db[task_id]
        for key, value in update_data.items():
            task[key] = value
        return task.copy()

    def delete(self, task_id: int) -> bool:
        if task_id in self.db:
            del self.db[task_id]
            return True
        return False
