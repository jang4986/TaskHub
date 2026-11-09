from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from taskhub.enums.common import TaskPriority, TaskStatus
from taskhub.models.base import Base

if TYPE_CHECKING:
    from taskhub.models.comment import Comment
    from taskhub.models.project import Project
    from taskhub.models.task_label import TaskLabel
    from taskhub.models.user import User


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, index=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    assignee_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), default=TaskStatus.TODO.value, nullable=False
    )
    priority: Mapped[str] = mapped_column(
        String(50), default=TaskPriority.MEDIUM.value, nullable=False
    )
    due_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_by: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="tasks",
        foreign_keys=[project_id],
    )
    assignee: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="tasks_assigned",
        foreign_keys=[assignee_id],
    )
    creator: Mapped["User"] = relationship(
        "User",
        back_populates="tasks_created",
        foreign_keys=[created_by],
    )
    task_labels: Mapped[list["TaskLabel"]] = relationship(
        "TaskLabel",
        back_populates="task",
        cascade="all, delete-orphan",
    )
    comments: Mapped[list["Comment"]] = relationship(
        "Comment",
        back_populates="task",
        cascade="all, delete-orphan",
    )
