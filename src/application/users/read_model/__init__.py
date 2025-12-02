"""Users read model DTOs.

**Feature: architecture-restructuring-2025**
**Validates: Requirements 4.1**
"""

from datetime import datetime
from pydantic import BaseModel, ConfigDict


class UserReadDTO(BaseModel):
    """User read model DTO."""

    model_config = ConfigDict(frozen=True)

    id: str
    email: str
    username: str | None = None
    display_name: str | None = None
    is_active: bool = True
    is_verified: bool = False
    created_at: datetime
    updated_at: datetime


class UserListReadDTO(BaseModel):
    """User list read model DTO."""

    model_config = ConfigDict(frozen=True)

    id: str
    email: str
    display_name: str | None = None
    is_active: bool = True


class UserSearchResultDTO(BaseModel):
    """User search result DTO."""

    model_config = ConfigDict(frozen=True)

    id: str
    email: str
    display_name: str | None = None
    match_score: float = 0.0


__all__ = [
    "UserReadDTO",
    "UserListReadDTO",
    "UserSearchResultDTO",
]
