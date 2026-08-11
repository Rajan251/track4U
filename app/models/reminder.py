from datetime import date, datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TenantMixin, TimestampMixin, generate_uuid

if TYPE_CHECKING:
    from app.models.org import Organization
    from app.models.user import User


class CustomReminder(Base, TimestampMixin, TenantMixin):
    """
    A user-defined reminder.
    Example: "Alert me 25 days before my Gmail password expires on Dec 1".

    Fields:
        title              - Short label, e.g. "Gmail Password Expiry"
        description        - Optional notes
        target_date        - The date something expires/happens
        remind_days_before - Start alerting when (target_date - today) <= this value
        repeat_interval_days - If set, reminder repeats every N days after target_date (for recurring tasks)
        is_active          - False to silence this reminder without deleting
        user_id            - Owner of this reminder
        org_id             - Organization scope (from TenantMixin)
    """

    __tablename__ = "custom_reminders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    org_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    target_date: Mapped[date] = mapped_column(Date, nullable=False)
    remind_days_before: Mapped[int] = mapped_column(Integer, default=7, nullable=False)
    repeat_interval_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Extra alert recipients for this reminder (comma-separated emails)
    alert_emails: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    organization: Mapped["Organization"] = relationship("Organization")
    user: Mapped["User"] = relationship("User")
    alert_logs: Mapped[list["ReminderAlertLog"]] = relationship(
        "ReminderAlertLog", back_populates="reminder", cascade="all, delete-orphan"
    )


class ReminderAlertLog(Base):
    """Tracks sent reminder alerts to prevent duplicate emails within the de-dup window."""

    __tablename__ = "reminder_alert_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    custom_reminder_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("custom_reminders.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    days_remaining_at_alert: Mapped[int] = mapped_column(Integer, nullable=False)
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(__import__("datetime").timezone.utc),
        nullable=False,
    )

    reminder: Mapped["CustomReminder"] = relationship(
        "CustomReminder", back_populates="alert_logs"
    )
