"""Write Model DTOs for the Users bounded context.

These DTOs are used for command operations (create, update, delete).
For read/query operations, use read_model.users_read.dto instead.

**Architecture: CQRS - Write Model**
**Feature: architecture-restructuring-2025**
**Validates: Requirements 3.6**
"""

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class UserDTO(BaseModel):
    """User data transfer object for API responses."""

    model_config = ConfigDict(frozen=True)

    id: str
    email: str
    username: str | None = None
    display_name: str | None = None
    is_active: bool = True
    is_verified: bool = False
    created_at: datetime
    updated_at: datetime
    last_login_at: datetime | None = None


class CreateUserDTO(BaseModel):
    """DTO for creating a new user."""

    model_config = ConfigDict(frozen=True)

    email: str = Field(
        ..., description="User email address", min_length=5, max_length=255
    )
    password: str = Field(..., min_length=8, description="User password")
    username: str | None = Field(default=None, min_length=3, max_length=50)
    display_name: str | None = Field(default=None, max_length=100)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", v):
            raise ValueError("Invalid email format")
        return v.lower()


class UpdateUserDTO(BaseModel):
    """DTO for updating a user."""

    model_config = ConfigDict(frozen=True)

    username: str | None = Field(default=None, min_length=3, max_length=50)
    display_name: str | None = Field(default=None, max_length=100)


class ChangePasswordDTO(BaseModel):
    """DTO for changing password."""

    model_config = ConfigDict(frozen=True)

    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password")


class ChangeEmailDTO(BaseModel):
    """DTO for changing email."""

    model_config = ConfigDict(frozen=True)

    new_email: str = Field(
        ..., description="New email address", min_length=5, max_length=255
    )
    password: str = Field(..., description="Current password for verification")

    @field_validator("new_email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", v):
            raise ValueError("Invalid email format")
        return v.lower()


class UserListDTO(BaseModel):
    """DTO for user list item."""

    model_config = ConfigDict(frozen=True)

    id: str
    email: str
    username: str | None = None
    display_name: str | None = None
    is_active: bool = True
    created_at: datetime
