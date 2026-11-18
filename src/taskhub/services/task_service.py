from taskhub.core.constants import DEFAULT_PAGE_SIZE
from taskhub.core.enums import TaskPriority, TaskStatus, UserRole, WorkspaceRole
from taskhub.core.exceptions import (
    AssigneeMustBeWorkspaceMemberError,
    AssigneeNotFoundError,
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
from taskhub.schemas.task import TaskCreate, TaskUpdate


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
            raise AssigneeNotFoundError(assignee_id)

        if project.workspace_id is not None:
            ws = await self.ws_repo.get(project.workspace_id)
            is_ws_owner = ws is not None and ws.owner_id == assignee_id
            member = await self.member_repo.get_member(project.workspace_id, assignee_id)

            if not (member is not None or is_ws_owner):
                raise AssigneeMustBeWorkspaceMemberError()

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
                    "Assignee for personal projects must be the project owner"
                )

    async def create_task(
        self,
        project_id: int,
        created_by: int,
        task_in: TaskCreate,
        current_user: User,
    ) -> Task:
        # Check project existence and permissions
        project = await self.check_project_access(
            project_id=project_id,
            user=current_user,
            require_write=True,
        )

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
            assignee_id=assignee_id_filter,
        )

    async def update_task(
        self,
        task_id: int,
        task_in: TaskUpdate,
        current_user: User,
    ) -> Task:
        task, project = await self.check_task_access(
            task_id=task_id,
            user=current_user,
            require_write=True,
        )

        # Validate new assignee if provided
        if task_in.assignee_id is not None:
            await self.validate_assignee_in_workspace(project, task_in.assignee_id)

        updated_task = await self.task_repo.update(db_obj=task, obj_in=task_in)
        await self.task_repo.db.commit()
        return updated_task

    async def delete_task(self, task_id: int, current_user: User) -> None:
        task, _ = await self.check_task_access(
            task_id=task_id,
            user=current_user,
            require_write=True,
        )
        await self.task_repo.remove(id=task.id)
        await self.task_repo.db.commit()
