"""User SQLAlchemy models for persistence.

**Feature: architecture-restructuring-2025**
**Validates: Requirements 6.1**
"""

from datetime import datetime
from typing import Any

from sqlalchemy import String, Boolean, DateTime, Text, Index
from sqlalchemy.orm import Mapped, mapped_column

from my_app.infrastructure.db.models.read_models import Base


class UserModel(Base):
    """User persistence model (write model).
    
    This model represents the user aggregate in the database
    and is used for write operations.
    """
    
    __tablename__ = "users"
    
    # Primary key
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    
    # Core user data
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    username: Mapped[str | None] = mapped_column(String(50), nullable=True, unique=True)
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
    
    # Version for optimistic locking
    version: Mapped[int] = mapped_column(default=1, nullable=False)
    
    # Indexes
    __table_args__ = (
        Index("ix_users_email", "email"),
        Index("ix_users_username", "username"),
        Index("ix_users_active", "is_active"),
    )
    
    def to_dict(self) -> dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "email": self.email,
            "password_hash": self.password_hash,
            "username": self.username,
            "display_name": self.display_name,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_login_at": self.last_login_at,
            "version": self.version,
        }
