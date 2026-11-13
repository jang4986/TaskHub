from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from taskhub.core.enums import ProjectStatus
from taskhub.models.base import Base

if TYPE_CHECKING:
    from taskhub.models.label import Label
    from taskhub.models.task import Task
    from taskhub.models.user import User
    from taskhub.models.workspace import Workspace


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, index=True)
    workspace_id: Mapped[int | None] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), default=ProjectStatus.ACTIVE.value, nullable=False
    )
    owner_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    workspace: Mapped[Optional["Workspace"]] = relationship(
        "Workspace",
        back_populates="projects",
        foreign_keys=[workspace_id],
    )
    owner: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="projects_owned",
        foreign_keys=[owner_id],
    )
    tasks: Mapped[list["Task"]] = relationship(
        "Task",
        back_populates="project",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    labels: Mapped[list["Label"]] = relationship(
        "Label",
        back_populates="project",
        cascade="all, delete-orphan",
    )
