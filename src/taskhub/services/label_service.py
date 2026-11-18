from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

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
from taskhub.repositories.label_repo import LabelRepository
from taskhub.repositories.project_repo import ProjectRepository
from taskhub.repositories.task_repo import TaskRepository
from taskhub.repositories.workspace_member_repo import WorkspaceMemberRepository
from taskhub.repositories.workspace_repo import WorkspaceRepository
from taskhub.schemas.label import LabelCreate, LabelUpdate
from taskhub.services.workspace_service import require_workspace_role

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

    async def check_project_write_access(self, project_id: int, user_id: int):
        project = await self.project_repo.get(project_id)
        if project is None:
            raise ProjectNotFoundError(project_id)

        if project.owner_id == user_id:
            return project

        if project.workspace_id is not None:
            await require_workspace_role(
                workspace_id=project.workspace_id,
                user_id=user_id,
                allowed_roles=WORKSPACE_LABEL_WRITE_ROLES,
                ws_repo=self.ws_repo,
                member_repo=self.member_repo,
                denied_detail="Viewers do not have permission to modify labels",
            )
            return project

        raise ProjectAccessDeniedError()

    async def check_project_read_access(self, project_id: int, user_id: int):
        project = await self.project_repo.get(project_id)
        if project is None:
            raise ProjectNotFoundError(project_id)

        if project.owner_id == user_id:
            return project

        if project.workspace_id is not None:
            await require_workspace_role(
                workspace_id=project.workspace_id,
                user_id=user_id,
                allowed_roles=None,
                ws_repo=self.ws_repo,
                member_repo=self.member_repo,
                denied_detail="Not a member of this workspace",
            )
            return project

        raise ProjectAccessDeniedError()

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

    async def update_label(self, label_id: int, user_id: int, data: LabelUpdate) -> Label:
        label = await self.label_repo.get(label_id)
        if label is None:
            raise LabelNotFoundError(label_id)

        try:
            await self.check_project_write_access(label.project_id, user_id)
        except (ProjectAccessDeniedError, WorkspaceAccessDeniedError):
            # Outsider without workspace access -> return 404 to prevent ID enumeration
            raise LabelNotFoundError(label_id) from None

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

    async def delete_label(self, label_id: int, user_id: int) -> None:
        label = await self.label_repo.get(label_id)
        if label is None:
            raise LabelNotFoundError(label_id)

        try:
            await self.check_project_write_access(label.project_id, user_id)
        except (ProjectAccessDeniedError, WorkspaceAccessDeniedError):
            raise LabelNotFoundError(label_id) from None

        await self.label_repo.remove(label_id)
        await self.db.commit()

    async def assign_label_to_task(self, task_id: int, label_id: int, user_id: int) -> Label:
        task = await self.task_repo.get(task_id)
        if task is None:
            raise TaskNotFoundError(task_id)

        # Check write access on task's project FIRST before inspecting label
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
            return label
        except IntegrityError:
            await self.db.rollback()
            raise LabelAlreadyAttachedError() from None


    async def remove_label_from_task(self, task_id: int, label_id: int, user_id: int) -> None:
        task = await self.task_repo.get(task_id)
        if task is None:
            raise TaskNotFoundError(task_id)

        # Check write access on task's project FIRST before inspecting label
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
