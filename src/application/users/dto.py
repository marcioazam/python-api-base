"""DTOs for the Users application layer.

**Feature: architecture-restructuring-2025**
**Validates: Requirements 3.6**
"""

from datetime import datetime

from pydantic import BaseModel, Field, EmailStr, ConfigDict


class UserDTO(BaseModel):
    """User data transfer object."""
    
    model_config = ConfigDict(frozen=True)
    """User data transfer object."""
    
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
    
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password")
    username: str | None = Field(default=None, min_length=3, max_length=50)
    display_name: str | None = Field(default=None, max_length=100)


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
    
    new_email: EmailStr = Field(..., description="New email address")
    password: str = Field(..., description="Current password for verification")


class UserListDTO(BaseModel):
    """DTO for user list item."""
    
    model_config = ConfigDict(frozen=True)
    
    id: str
    email: str
    username: str | None = None
    display_name: str | None = None
    is_active: bool = True
    created_at: datetime
