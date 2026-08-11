from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, generate_uuid

if TYPE_CHECKING:
    from app.models.task import Task


class TaskAlertLog(Base):
    """Tracks sent task due-date alert emails to prevent duplicates within the de-dup window."""

    __tablename__ = "task_alert_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    task_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    days_remaining_at_alert: Mapped[int] = mapped_column(Integer, nullable=False)
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(__import__("datetime").timezone.utc),
        nullable=False,
    )

    task: Mapped["Task"] = relationship("Task", back_populates="alert_logs")
