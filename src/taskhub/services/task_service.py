
from sqlalchemy import select

from taskhub.core.constants import DEFAULT_PAGE_SIZE
from taskhub.core.enums import TaskPriority, TaskStatus, UserRole, WorkspaceRole
from taskhub.core.exceptions import (
    AssigneeNotFoundError,
    InsufficientPrivilegesError,
    ProjectAccessDeniedError,
    ProjectNotFoundError,
    TaskNotFoundError,
    UserNotFoundError,
)
from taskhub.models.project import Project
from taskhub.models.task import Task
from taskhub.models.user import User
from taskhub.models.workspace import Workspace
from taskhub.models.workspace_member import WorkspaceMember
from taskhub.repositories.task_repo import TaskRepository
from taskhub.schemas.task import TaskCreate, TaskUpdate


class TaskService:
    def __init__(self, task_repo: TaskRepository) -> None:
        self.task_repo = task_repo

    async def check_project_access(
        self,
        project_id: int,
        user: User,
        require_write: bool = False,
    ) -> Project:
        project = await self.task_repo.db.get(Project, project_id)
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
            workspace = await self.task_repo.db.get(Workspace, project.workspace_id)
            if workspace is not None and workspace.owner_id == user.id:
                return project

            # Check workspace membership role
            stmt = select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == project.workspace_id,
                WorkspaceMember.user_id == user.id,
            )
            res = await self.task_repo.db.execute(stmt)
            member = res.scalar_one_or_none()
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
    ) -> Task:
        task = await self.task_repo.get(task_id)
        if task is None:
            raise TaskNotFoundError(task_id)

        await self.check_project_access(
            project_id=task.project_id,
            user=user,
            require_write=require_write,
        )
        return task

    async def create_task(
        self,
        project_id: int,
        created_by: int,
        task_in: TaskCreate,
        current_user: User,
    ) -> Task:
        # Check project existence and permissions
        await self.check_project_access(
            project_id=project_id,
            user=current_user,
            require_write=True,
        )

        # Validate created_by user exists
        creator = await self.task_repo.db.get(User, created_by)
        if creator is None:
            raise UserNotFoundError(created_by)

        # Validate assignee exists if provided
        if task_in.assignee_id is not None:
            assignee = await self.task_repo.db.get(User, task_in.assignee_id)
            if assignee is None:
                raise AssigneeNotFoundError(task_in.assignee_id)

        task = await self.task_repo.create_with_project(
            project_id=project_id,
            created_by=created_by,
            obj_in=task_in,
        )
        await self.task_repo.db.commit()
        return task

    async def get_task(self, task_id: int, current_user: User) -> Task:
        return await self.check_task_access(
            task_id=task_id,
            user=current_user,
            require_write=False,
        )

    async def get_project_tasks(
        self,
        project_id: int,
        current_user: User,
        skip: int = 0,
        limit: int = DEFAULT_PAGE_SIZE,
        status_filter: TaskStatus | str | None = None,
        priority_filter: TaskPriority | str | None = None,
    ) -> tuple[list[Task], int]:
        await self.check_project_access(
            project_id=project_id,
            user=current_user,
            require_write=False,
        )
        return await self.task_repo.get_by_project(
            project_id=project_id,
            skip=skip,
            limit=limit,
            status=status_filter,
            priority=priority_filter,
        )

    async def update_task(
        self,
        task_id: int,
        task_in: TaskUpdate,
        current_user: User,
    ) -> Task:
        task = await self.check_task_access(
            task_id=task_id,
            user=current_user,
            require_write=True,
        )

        # Validate new assignee if provided
        if task_in.assignee_id is not None:
            assignee = await self.task_repo.db.get(User, task_in.assignee_id)
            if assignee is None:
                raise AssigneeNotFoundError(task_in.assignee_id)

        updated_task = await self.task_repo.update(db_obj=task, obj_in=task_in)
        await self.task_repo.db.commit()
        return updated_task

    async def delete_task(self, task_id: int, current_user: User) -> None:
        task = await self.check_task_access(
            task_id=task_id,
            user=current_user,
            require_write=True,
        )
        await self.task_repo.remove(id=task.id)
        await self.task_repo.db.commit()
