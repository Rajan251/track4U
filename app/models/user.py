from typing import TYPE_CHECKING, List

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, generate_uuid

if TYPE_CHECKING:
    from app.models.org import OrgMember


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    notify_on_expiry: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    org_memberships: Mapped[List["OrgMember"]] = relationship(
        "OrgMember", back_populates="user", cascade="all, delete-orphan"
    )
