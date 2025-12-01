"""Read model DTOs for Users bounded context.

These DTOs are optimized for read operations and may contain
denormalized data for efficient querying.

**Feature: architecture-restructuring-2025**
**Validates: Requirements 4.1**
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class UserReadDTO:
    """Read-optimized user data transfer object.
    
    Contains all user data needed for display purposes,
    potentially denormalized for efficient queries.
    """
    
    id: str
    email: str
    username: str | None = None
    display_name: str | None = None
    is_active: bool = True
    is_verified: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None
    last_login_at: datetime | None = None
    
    # Denormalized fields for display
    role_names: tuple[str, ...] = ()
    permission_count: int = 0
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "email": self.email,
            "username": self.username,
            "display_name": self.display_name,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
            "role_names": list(self.role_names),
            "permission_count": self.permission_count,
        }


@dataclass(frozen=True, slots=True)
class UserListReadDTO:
    """Lightweight user DTO for list views.
    
    Contains minimal data needed for user listings.
    """
    
    id: str
    email: str
    display_name: str | None = None
    is_active: bool = True
    created_at: datetime | None = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "email": self.email,
            "display_name": self.display_name,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


@dataclass(frozen=True, slots=True)
class UserSearchResultDTO:
    """User search result DTO with relevance score.
    
    Used for search results with ranking information.
    """
    
    id: str
    email: str
    display_name: str | None = None
    relevance_score: float = 0.0
    matched_fields: tuple[str, ...] = ()
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "email": self.email,
            "display_name": self.display_name,
            "relevance_score": self.relevance_score,
            "matched_fields": list(self.matched_fields),
        }


@dataclass(frozen=True, slots=True)
class UserActivityReadDTO:
    """User activity summary for dashboard views."""
    
    user_id: str
    total_logins: int = 0
    last_login_at: datetime | None = None
    last_activity_at: datetime | None = None
    active_sessions: int = 0
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "user_id": self.user_id,
            "total_logins": self.total_logins,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
            "last_activity_at": self.last_activity_at.isoformat() if self.last_activity_at else None,
            "active_sessions": self.active_sessions,
        }
