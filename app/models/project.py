from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TenantMixin, TimestampMixin, generate_uuid

if TYPE_CHECKING:
    from app.models.org import Organization
    from app.models.task import Task


class Project(Base, TimestampMixin, TenantMixin):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    org_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), default="active", nullable=False
    )  # active, archived, completed

    organization: Mapped["Organization"] = relationship("Organization", back_populates="projects")
    tasks: Mapped[List["Task"]] = relationship(
        "Task", back_populates="project", cascade="all, delete-orphan"
    )
