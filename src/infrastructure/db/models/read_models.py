"""Read model SQLAlchemy models for optimized queries.

These models represent denormalized views of domain data,
optimized for read operations in CQRS pattern.

**Feature: architecture-restructuring-2025**
**Validates: Requirements 4.3, 6.1**
"""

from datetime import datetime
from typing import Any

from sqlalchemy import String, Boolean, DateTime, Integer, Index, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


class UserReadModel(Base):
    """Read-optimized user model for queries.

    This model is updated by projections from domain events
    and provides efficient query access to user data.
    """

    __tablename__ = "users_read"

    # Primary key
    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # Core user data
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    username: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    display_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Status flags
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Denormalized data for efficient queries
    role_names: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Comma-separated list of role names",
    )
    permission_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    # Deactivation info
    deactivation_reason: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    # Indexes for common queries
    __table_args__ = (
        Index("ix_users_read_active_created", "is_active", "created_at"),
        Index("ix_users_read_email_active", "email", "is_active"),
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "email": self.email,
            "username": self.username,
            "display_name": self.display_name,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_login_at": self.last_login_at.isoformat()
            if self.last_login_at
            else None,
            "role_names": self.role_names.split(",") if self.role_names else [],
            "permission_count": self.permission_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UserReadModel":
        """Create model from dictionary."""
        role_names = data.get("role_names")
        if isinstance(role_names, list):
            role_names = ",".join(role_names)

        return cls(
            id=data["id"],
            email=data["email"],
            username=data.get("username"),
            display_name=data.get("display_name"),
            is_active=data.get("is_active", True),
            is_verified=data.get("is_verified", False),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            last_login_at=data.get("last_login_at"),
            role_names=role_names,
            permission_count=data.get("permission_count", 0),
            deactivation_reason=data.get("deactivation_reason"),
        )
