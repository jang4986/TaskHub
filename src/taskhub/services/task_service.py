from typing import Any

from fastapi import BackgroundTasks

from taskhub.core.cache import (
    build_project_tasks_cache_key,
    get_cache,
    invalidate_project_tasks_cache,
    set_cache,
)
from taskhub.core.constants import DEFAULT_PAGE_SIZE
from taskhub.core.enums import TaskPriority, TaskStatus, UserRole, WorkspaceRole
from taskhub.core.exceptions import (
    AssigneeMustBeWorkspaceMemberError,
    AssigneeRoleNotAllowedError,
    InsufficientPrivilegesError,
    ProjectAccessDeniedError,
    ProjectNotFoundError,
    TaskNotFoundError,
    UserNotFoundError,
)
from taskhub.models.project import Project
from taskhub.models.task import Task
from taskhub.models.user import User
from taskhub.repositories.project_repo import ProjectRepository
from taskhub.repositories.task_repo import TaskRepository
from taskhub.repositories.user_repo import UserRepository
from taskhub.repositories.workspace_member_repo import WorkspaceMemberRepository
from taskhub.repositories.workspace_repo import WorkspaceRepository
from taskhub.schemas.task import TaskCreate, TaskResponse, TaskUpdate
from taskhub.services.notification_service import send_task_assigned_notification
from taskhub.services.project_service import ensure_project_writable


class TaskService:
    def __init__(
        self,
        task_repo: TaskRepository,
        project_repo: ProjectRepository | None = None,
        ws_repo: WorkspaceRepository | None = None,
        member_repo: WorkspaceMemberRepository | None = None,
        user_repo: UserRepository | None = None,
    ) -> None:
        self.task_repo = task_repo
        self.project_repo = project_repo or ProjectRepository(db=task_repo.db)
        self.ws_repo = ws_repo or WorkspaceRepository(db=task_repo.db)
        self.member_repo = member_repo or WorkspaceMemberRepository(db=task_repo.db)
        self.user_repo = user_repo or UserRepository(db=task_repo.db)

    async def check_project_access(
        self,
        project_id: int,
        user: User,
        require_write: bool = False,
    ) -> Project:
        project = await self.project_repo.get(project_id)
        if project is None:
            raise ProjectNotFoundError(project_id)

        # 1. Admin has global access
        user_role_val = user.role.value if hasattr(user.role, "value") else str(user.role)
        if user_role_val == UserRole.ADMIN.value:
            return project

        # 2. Project owner has full access
        if project.owner_id is not None and project.owner_id == user.id:
            return project

        # 3. Workspace level access
        if project.workspace_id is not None:
            workspace = await self.ws_repo.get(project.workspace_id)
            if workspace is not None and workspace.owner_id == user.id:
                return project

            # Check workspace membership role
            member = await self.member_repo.get_member(project.workspace_id, user.id)
            if member is not None:
                member_role_val = (
                    member.role.value if hasattr(member.role, "value") else str(member.role)
                )
                if require_write and member_role_val == WorkspaceRole.VIEWER.value:
                    raise InsufficientPrivilegesError(
                        "Viewers do not have permission to modify tasks in this project"
                    )
                return project

        # No access allowed
        raise ProjectAccessDeniedError()

    async def check_task_access(
        self,
        task_id: int,
        user: User,
        require_write: bool = False,
    ) -> tuple[Task, Project]:
        task = await self.task_repo.get(task_id)
        if task is None:
            raise TaskNotFoundError(task_id)

        project = await self.check_project_access(
            project_id=task.project_id,
            user=user,
            require_write=require_write,
        )
        return task, project

    async def validate_assignee_in_workspace(self, project: Project, assignee_id: int) -> None:
        assignee = await self.user_repo.get(assignee_id)
        if assignee is None:
            raise AssigneeMustBeWorkspaceMemberError(
                "Assignee must be a member of the project's workspace"
            )

        if project.workspace_id is not None:
            ws = await self.ws_repo.get(project.workspace_id)
            is_ws_owner = ws is not None and ws.owner_id == assignee_id
            member = await self.member_repo.get_member(project.workspace_id, assignee_id)

            if not (member is not None or is_ws_owner):
                raise AssigneeMustBeWorkspaceMemberError(
                    "Assignee must be a member of the project's workspace"
                )

            if member is not None and not is_ws_owner:
                member_role_val = (
                    member.role.value if hasattr(member.role, "value") else str(member.role)
                )
                if member_role_val == WorkspaceRole.VIEWER.value:
                    raise AssigneeRoleNotAllowedError()
        else:
            # Personal project without workspace: assignee must be project owner
            if project.owner_id is not None and assignee_id != project.owner_id:
                raise AssigneeMustBeWorkspaceMemberError(
                    "Assignee must be a member of the project's workspace"
                )

    async def create_task(
        self,
        project_id: int,
        created_by: int,
        task_in: TaskCreate,
        current_user: User,
        background_tasks: BackgroundTasks | None = None,
    ) -> Task:
        # Check project existence and permissions
        project = await self.check_project_access(
            project_id=project_id,
            user=current_user,
            require_write=True,
        )

        ensure_project_writable(project)

        # Validate created_by user exists
        creator = await self.user_repo.get(created_by)
        if creator is None:
            raise UserNotFoundError(created_by)

        # Validate assignee exists, belongs to workspace, and has write access
        if task_in.assignee_id is not None:
            await self.validate_assignee_in_workspace(project, task_in.assignee_id)

        task = await self.task_repo.create_with_project(
            project_id=project_id,
            created_by=created_by,
            obj_in=task_in,
        )
        await self.task_repo.db.commit()
        await invalidate_project_tasks_cache(project_id)

        if background_tasks is not None and task.assignee_id is not None:
            background_tasks.add_task(
                send_task_assigned_notification,
                task.assignee_id,
                task.id,
                task.title,
            )

        return task

    async def get_task(self, task_id: int, current_user: User) -> Task:
        task, _ = await self.check_task_access(
            task_id=task_id,
            user=current_user,
            require_write=False,
        )
        return task

    async def get_project_tasks(
        self,
        project_id: int,
        current_user: User,
        skip: int = 0,
        limit: int = DEFAULT_PAGE_SIZE,
        status_filter: TaskStatus | str | None = None,
        priority_filter: TaskPriority | str | None = None,
        assignee_id_filter: int | None = None,
    ) -> tuple[list[Any], int, bool]:
        await self.check_project_access(
            project_id=project_id,
            user=current_user,
            require_write=False,
        )

        cache_key = build_project_tasks_cache_key(
            project_id=project_id,
            status=status_filter,
            priority=priority_filter,
            assignee_id=assignee_id_filter,
            offset=skip,
            limit=limit,
        )

        cached_data = await get_cache(cache_key)
        if cached_data is not None and isinstance(cached_data, dict):
            items = cached_data.get("items", [])
            total = cached_data.get("total", 0)
            return items, total, True

        tasks, total = await self.task_repo.get_by_project(
            project_id=project_id,
            skip=skip,
            limit=limit,
            status=status_filter,
            priority=priority_filter,
            assignee_id=assignee_id_filter,
        )

        items_serialized = [TaskResponse.model_validate(t).model_dump(mode="json") for t in tasks]
        await set_cache(cache_key, {"items": items_serialized, "total": total})

        return list(tasks), total, False

    async def update_task(
        self,
        task_id: int,
        task_in: TaskUpdate,
        current_user: User,
        background_tasks: BackgroundTasks | None = None,
    ) -> Task:
        task, project = await self.check_task_access(
            task_id=task_id,
            user=current_user,
            require_write=True,
        )

        ensure_project_writable(project)

        # Validate new assignee if provided
        if task_in.assignee_id is not None:
            await self.validate_assignee_in_workspace(project, task_in.assignee_id)

        old_assignee_id = task.assignee_id

        updated_task = await self.task_repo.update(db_obj=task, obj_in=task_in)
        await self.task_repo.db.commit()
        await invalidate_project_tasks_cache(task.project_id)

        if (
            background_tasks is not None
            and updated_task.assignee_id is not None
            and updated_task.assignee_id != old_assignee_id
        ):
            background_tasks.add_task(
                send_task_assigned_notification,
                updated_task.assignee_id,
                updated_task.id,
                updated_task.title,
            )

        return updated_task

    async def delete_task(self, task_id: int, current_user: User) -> None:
        task, project = await self.check_task_access(
            task_id=task_id,
            user=current_user,
            require_write=True,
        )

        ensure_project_writable(project)

        project_id = task.project_id
        await self.task_repo.remove(id=task.id)
        await self.task_repo.db.commit()
        await invalidate_project_tasks_cache(project_id)
