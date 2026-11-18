from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from taskhub.core.constants import DEFAULT_LABEL_COLOR, LABEL_NAME_MAX_LENGTH
from taskhub.models.base import Base

if TYPE_CHECKING:
    from taskhub.models.project import Project
    from taskhub.models.task_label import TaskLabel


class Label(Base):
    __tablename__ = "labels"
    __table_args__ = (UniqueConstraint("project_id", "name", name="uq_labels_project_name"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, index=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(LABEL_NAME_MAX_LENGTH), nullable=False)
    color: Mapped[str] = mapped_column(String(50), default=DEFAULT_LABEL_COLOR, nullable=False)

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="labels")
    task_labels: Mapped[list["TaskLabel"]] = relationship(
        "TaskLabel",
        back_populates="label",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
