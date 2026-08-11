from datetime import date
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TenantMixin, TimestampMixin, generate_uuid

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.task_alert import TaskAlertLog
    from app.models.user import User


class TaskLabel(Base):
    __tablename__ = "task_labels"

    task_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True
    )
    label_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("labels.id", ondelete="CASCADE"), primary_key=True
    )


class Label(Base, TimestampMixin, TenantMixin):
    __tablename__ = "labels"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    org_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    color: Mapped[str] = mapped_column(String(50), default="#3B82F6", nullable=False)

    tasks: Mapped[List["Task"]] = relationship(
        "Task", secondary="task_labels", back_populates="labels"
    )


class Task(Base, TimestampMixin, TenantMixin):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    org_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), default="todo", nullable=False
    )  # todo, in_progress, done
    priority: Mapped[str] = mapped_column(
        String(50), default="medium", nullable=False
    )  # low, medium, high, urgent
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    assignee_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    # Alert configuration — per-task email recipients and warning window
    alert_emails: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # comma-separated
    alert_days_before: Mapped[int] = mapped_column(Integer, default=3, nullable=False)

    project: Mapped["Project"] = relationship("Project", back_populates="tasks")
    assignee: Mapped[Optional["User"]] = relationship("User", foreign_keys=[assignee_id])
    creator: Mapped["User"] = relationship("User", foreign_keys=[created_by])
    labels: Mapped[List["Label"]] = relationship(
        "Label", secondary="task_labels", back_populates="tasks"
    )
    comments: Mapped[List["Comment"]] = relationship(
        "Comment", back_populates="task", cascade="all, delete-orphan"
    )
    activity_logs: Mapped[List["ActivityLog"]] = relationship(
        "ActivityLog", back_populates="task", cascade="all, delete-orphan"
    )
    alert_logs: Mapped[List["TaskAlertLog"]] = relationship(
        "TaskAlertLog", back_populates="task", cascade="all, delete-orphan"
    )


class Comment(Base, TimestampMixin):
    __tablename__ = "comments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    task_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tasks.id", ondelete="CASCADE"), index=True, nullable=False
    )
    author_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)

    task: Mapped["Task"] = relationship("Task", back_populates="comments")
    author: Mapped["User"] = relationship("User")


class ActivityLog(Base, TimestampMixin):
    __tablename__ = "activity_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    task_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tasks.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    action: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # created, status_changed, assigned, etc.
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    task: Mapped["Task"] = relationship("Task", back_populates="activity_logs")
    user: Mapped["User"] = relationship("User")
