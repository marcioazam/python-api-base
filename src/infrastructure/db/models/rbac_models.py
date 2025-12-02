"""RBAC SQLAlchemy models for persistence.

Provides database models for Role-Based Access Control:
- RoleModel: Stores role definitions
- UserRoleModel: Maps users to roles
- PermissionModel: Stores permissions (optional fine-grained control)

**Feature: core-rbac-system**
**Part of: Core API (not example - permanent)**
"""

from datetime import datetime
from typing import Any

from sqlalchemy import String, Boolean, DateTime, ForeignKey, Text, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.db.models.read_models import Base
from core.shared.utils.datetime import utc_now


class RoleModel(Base):
    """Role persistence model.

    Stores role definitions with their permissions.
    """

    __tablename__ = "roles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, nullable=True, default="")
    permissions: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=[])
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    # Relationships
    user_roles: Mapped[list["UserRoleModel"]] = relationship(
        back_populates="role",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_roles_name", "name"),
        Index("ix_roles_active", "is_active"),
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "permissions": self.permissions,
            "is_system": self.is_system,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class UserRoleModel(Base):
    """User-Role mapping model.

    Associates users with roles for access control.
    """

    __tablename__ = "user_roles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    role_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("roles.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Timestamps
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    assigned_by: Mapped[str | None] = mapped_column(String(36), nullable=True)

    # Relationships
    role: Mapped["RoleModel"] = relationship(back_populates="user_roles")

    __table_args__ = (
        Index("ix_user_roles_user_id", "user_id"),
        Index("ix_user_roles_role_id", "role_id"),
        Index("ix_user_roles_unique", "user_id", "role_id", unique=True),
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "role_id": self.role_id,
            "assigned_at": self.assigned_at.isoformat() if self.assigned_at else None,
            "assigned_by": self.assigned_by,
        }
