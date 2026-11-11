import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from taskhub.core.enums import NotificationType, ProjectStatus, TaskPriority, TaskStatus, UserRole, WorkspaceRole
from taskhub.models.comment import Comment
from taskhub.models.label import Label
from taskhub.models.notification import Notification
from taskhub.models.project import Project
from taskhub.models.task import Task
from taskhub.models.task_label import TaskLabel
from taskhub.models.user import User
from taskhub.models.workspace import Workspace
from taskhub.models.workspace_member import WorkspaceMember
from taskhub.repositories.comment_repo import CommentRepository
from taskhub.repositories.label_repo import LabelRepository
from taskhub.repositories.project_repo import ProjectRepository
from taskhub.repositories.task_repo import TaskRepository
from taskhub.repositories.user_repo import UserRepository
from taskhub.repositories.workspace_repo import WorkspaceRepository
from tests.conftest import TestingSessionLocal


@pytest.mark.asyncio
async def test_full_domain_models_and_repositories():
    async with TestingSessionLocal() as session:
        user_repo = UserRepository(db=session)
        ws_repo = WorkspaceRepository(db=session)
        proj_repo = ProjectRepository(db=session)
        task_repo = TaskRepository(db=session)
        label_repo = LabelRepository(db=session)
        comment_repo = CommentRepository(db=session)

        # 1. User
        user = await user_repo.get_by_email("user1@example.com")
        assert user is not None
        assert user.role == UserRole.MEMBER

        # 2. Workspace
        workspaces = await ws_repo.get_by_owner(owner_id=user.id)
        assert len(workspaces) >= 1
        ws = workspaces[0]

        # 3. Workspace Member
        member = await session.get(WorkspaceMember, (ws.id, 2))
        if member is None:
            member = WorkspaceMember(workspace_id=ws.id, user_id=2, role=WorkspaceRole.MEMBER.value)
            session.add(member)
            await session.flush()
        assert member.role == WorkspaceRole.MEMBER.value

        # 4. Project
        projects = await proj_repo.get_by_workspace(workspace_id=ws.id)
        assert len(projects) >= 1
        project = projects[0]

        # 5. Task
        task_created = await task_repo.create({
            "project_id": project.id,
            "assignee_id": 2,
            "title": "Build Architecture",
            "description": "Layered architecture implementation",
            "status": TaskStatus.TODO,
            "priority": TaskPriority.HIGH,
            "created_by": user.id,
        })
        assert task_created.id is not None
        assert task_created.title == "Build Architecture"

        # 6. Label
        label = await label_repo.create({
            "project_id": project.id,
            "name": "Backend",
            "color": "#10B981",
        })
        assert label.id is not None

        # 7. Task Label
        task_label = TaskLabel(task_id=task_created.id, label_id=label.id)
        session.add(task_label)
        await session.flush()

        # 8. Comment
        comment = await comment_repo.create({
            "task_id": task_created.id,
            "author_id": user.id,
            "content": "Work is progressing well",
        })
        assert comment.id is not None
        comments = await comment_repo.get_by_task(task_id=task_created.id)
        assert len(comments) == 1

        # 9. Notification
        notification = Notification(
            user_id=2,
            type=NotificationType.TASK_ASSIGNED.value,
            title="New Task Assigned",
            message="You have been assigned to Build Architecture",
            is_read=False,
        )
        session.add(notification)
        await session.flush()
        assert notification.id is not None

        await session.commit()
