from datetime import date, datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TenantMixin, TimestampMixin, generate_uuid

if TYPE_CHECKING:
    from app.models.org import Organization
    from app.models.user import User


class TrackedWebsite(Base, TimestampMixin, TenantMixin):
    __tablename__ = "tracked_websites"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    org_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    added_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    url: Mapped[str] = mapped_column(String(512), nullable=False)
    label: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    domain_expiry_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    ssl_expiry_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    last_checked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_check_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # ok, error
    last_check_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="tracked_websites"
    )
    user: Mapped["User"] = relationship("User")
    alert_logs: Mapped[List["ExpiryAlertLog"]] = relationship(
        "ExpiryAlertLog", back_populates="website", cascade="all, delete-orphan"
    )


class ExpiryAlertLog(Base):
    __tablename__ = "expiry_alert_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    tracked_website_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tracked_websites.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)  # domain, ssl
    days_remaining_at_alert: Mapped[int] = mapped_column(Integer, nullable=False)
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(__import__("datetime").timezone.utc),
        nullable=False,
    )

    website: Mapped["TrackedWebsite"] = relationship("TrackedWebsite", back_populates="alert_logs")
