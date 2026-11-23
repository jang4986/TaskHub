from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from taskhub.core.cache import invalidate_project_tasks_cache
from taskhub.core.enums import WorkspaceRole
from taskhub.core.exceptions import (
    FieldCannotBeNullError,
    LabelAlreadyAttachedError,
    LabelAlreadyExistsError,
    LabelNotAttachedError,
    LabelNotFoundError,
    LabelProjectMismatchError,
    ProjectAccessDeniedError,
    ProjectNotFoundError,
    TaskNotFoundError,
    WorkspaceAccessDeniedError,
)
from taskhub.models.label import Label
from taskhub.models.project import Project
from taskhub.repositories.label_repo import LabelRepository
from taskhub.repositories.project_repo import ProjectRepository
from taskhub.repositories.task_repo import TaskRepository
from taskhub.repositories.workspace_member_repo import WorkspaceMemberRepository
from taskhub.repositories.workspace_repo import WorkspaceRepository
from taskhub.schemas.label import LabelCreate, LabelUpdate
from taskhub.services.project_service import (
    ensure_project_writable,
    require_project_access,
)

WORKSPACE_LABEL_WRITE_ROLES = {
    WorkspaceRole.OWNER,
    WorkspaceRole.ADMIN,
    WorkspaceRole.EDITOR,
    WorkspaceRole.MEMBER,
}


class LabelService:
    def __init__(
        self,
        db: AsyncSession,
        label_repo: LabelRepository,
        project_repo: ProjectRepository,
        task_repo: TaskRepository,
        ws_repo: WorkspaceRepository,
        member_repo: WorkspaceMemberRepository,
    ) -> None:
        self.db = db
        self.label_repo = label_repo
        self.project_repo = project_repo
        self.task_repo = task_repo
        self.ws_repo = ws_repo
        self.member_repo = member_repo

    async def check_project_write_access(self, project_id: int, user_id: int) -> Project:
        project = await self.project_repo.get(project_id)
        if project is None:
            raise ProjectNotFoundError(project_id)

        # Check permissions first to prevent leaking archive status to outsiders
        await require_project_access(
            project=project,
            user_id=user_id,
            ws_repo=self.ws_repo,
            member_repo=self.member_repo,
            allowed_roles=WORKSPACE_LABEL_WRITE_ROLES,
            denied_detail="Viewers do not have permission to modify labels",
        )

        # Enforce project writable check only after permission check passes
        ensure_project_writable(project, "Cannot modify labels in an archived project")
        return project

    async def check_project_read_access(self, project_id: int, user_id: int) -> Project:
        project = await self.project_repo.get(project_id)
        if project is None:
            raise ProjectNotFoundError(project_id)

        await require_project_access(
            project=project,
            user_id=user_id,
            ws_repo=self.ws_repo,
            member_repo=self.member_repo,
            allowed_roles=None,
            denied_detail="Not a member of this workspace",
        )
        return project

    async def _get_label_for_write(self, label_id: int, user_id: int) -> tuple[Label, Project]:
        label = await self.label_repo.get(label_id)
        if label is None:
            raise LabelNotFoundError(label_id)

        project = await self.project_repo.get(label.project_id)
        if project is None:
            raise LabelNotFoundError(label_id)

        # Check permissions first; strangers get 404 (hiding label existence)
        # but VIEWERs get 403 (they know the project, just lack write access)
        try:
            await require_project_access(
                project=project,
                user_id=user_id,
                ws_repo=self.ws_repo,
                member_repo=self.member_repo,
                allowed_roles=WORKSPACE_LABEL_WRITE_ROLES,
                denied_detail="Viewers do not have permission to modify labels",
            )
        except (ProjectAccessDeniedError, WorkspaceAccessDeniedError) as exc:
            # Non-members receive 404 to hide label existence;
            # members with insufficient role receive the original 403.
            if "Not a member" in str(exc.detail):
                raise LabelNotFoundError(label_id) from None
            raise

        ensure_project_writable(project, "Cannot modify labels in an archived project")
        return label, project

    async def create_label(self, project_id: int, user_id: int, data: LabelCreate) -> Label:
        await self.check_project_write_access(project_id, user_id)

        existing = await self.label_repo.get_by_project_and_name(project_id, data.name)
        if existing is not None:
            raise LabelAlreadyExistsError(data.name)

        label = Label(
            project_id=project_id,
            name=data.name,
            color=data.color,
        )
        self.db.add(label)
        try:
            await self.db.commit()
            await self.db.refresh(label)
            return label
        except IntegrityError:
            await self.db.rollback()
            raise LabelAlreadyExistsError(data.name) from None

    async def list_labels(self, project_id: int, user_id: int) -> list[Label]:
        await self.check_project_read_access(project_id, user_id)
        return await self.label_repo.get_by_project(project_id)

    async def list_project_labels(
        self,
        project_id: int,
        user_id: int,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[Label], int]:
        await self.check_project_read_access(project_id, user_id)
        return await self.label_repo.get_by_project_paginated(
            project_id=project_id,
            skip=skip,
            limit=limit,
        )

    async def update_label(self, label_id: int, user_id: int, data: LabelUpdate) -> Label:
        label, _ = await self._get_label_for_write(label_id, user_id)

        update_dict = data.model_dump(exclude_unset=True)
        if "name" in update_dict:
            if update_dict["name"] is None:
                raise FieldCannotBeNullError("name")
            new_name = update_dict["name"]
            if new_name != label.name:
                existing = await self.label_repo.get_by_project_and_name(label.project_id, new_name)
                if existing is not None:
                    raise LabelAlreadyExistsError(new_name)
                label.name = new_name

        if "color" in update_dict:
            if update_dict["color"] is None:
                raise FieldCannotBeNullError("color")
            label.color = update_dict["color"]

        self.db.add(label)
        try:
            await self.db.commit()
            await self.db.refresh(label)
            return label
        except IntegrityError:
            await self.db.rollback()
            raise LabelAlreadyExistsError(label.name) from None

    async def delete_label(self, label_id: int, user_id: int) -> bool:
        label, _ = await self._get_label_for_write(label_id, user_id)
        await self.label_repo.remove(label_id)
        await self.db.commit()
        return True

    async def add_label_to_task(self, task_id: int, label_id: int, user_id: int) -> Label:
        task = await self.task_repo.get(task_id)
        if task is None:
            raise TaskNotFoundError(task_id)

        # Check write access on task's project FIRST before inspecting label or archive state
        await self.check_project_write_access(task.project_id, user_id)

        label = await self.label_repo.get(label_id)
        if label is None:
            raise LabelNotFoundError(label_id)

        if task.project_id != label.project_id:
            raise LabelProjectMismatchError()

        if await self.label_repo.is_attached(task_id, label_id):
            raise LabelAlreadyAttachedError()

        try:
            await self.label_repo.attach_to_task(task_id, label_id)
            await self.db.commit()
            await invalidate_project_tasks_cache(task.project_id)
            return label
        except IntegrityError:
            await self.db.rollback()
            raise LabelAlreadyAttachedError() from None

    async def assign_label_to_task(self, task_id: int, label_id: int, user_id: int) -> Label:
        return await self.add_label_to_task(task_id=task_id, label_id=label_id, user_id=user_id)

    async def remove_label_from_task(self, task_id: int, label_id: int, user_id: int) -> bool:
        task = await self.task_repo.get(task_id)
        if task is None:
            raise TaskNotFoundError(task_id)

        # Check write access on task's project FIRST before inspecting label or archive state
        await self.check_project_write_access(task.project_id, user_id)

        label = await self.label_repo.get(label_id)
        if label is None:
            raise LabelNotFoundError(label_id)

        if task.project_id != label.project_id:
            raise LabelProjectMismatchError()

        detached = await self.label_repo.detach_from_task(task_id, label_id)
        if not detached:
            raise LabelNotAttachedError()

        await self.db.commit()
        await invalidate_project_tasks_cache(task.project_id)
        return True
