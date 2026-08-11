from typing import TYPE_CHECKING, List

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, generate_uuid

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.user import User
    from app.models.website import TrackedWebsite


class Organization(Base, TimestampMixin):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    subscription_status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)
    plan_type: Mapped[str] = mapped_column(String(50), default="free", nullable=False)

    members: Mapped[List["OrgMember"]] = relationship(
        "OrgMember", back_populates="org", cascade="all, delete-orphan"
    )
    projects: Mapped[List["Project"]] = relationship(
        "Project", back_populates="organization", cascade="all, delete-orphan"
    )
    tracked_websites: Mapped[List["TrackedWebsite"]] = relationship(
        "TrackedWebsite", back_populates="organization", cascade="all, delete-orphan"
    )


class OrgMember(Base, TimestampMixin):
    __tablename__ = "org_members"
    __table_args__ = (UniqueConstraint("org_id", "user_id", name="uq_org_user"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    org_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(
        String(50), default="member", nullable=False
    )  # owner, admin, member

    org: Mapped["Organization"] = relationship("Organization", back_populates="members")
    user: Mapped["User"] = relationship("User", back_populates="org_memberships")
