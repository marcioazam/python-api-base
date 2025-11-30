"""Role and UserRole domain entities for RBAC.

**Feature: api-base-improvements**
**Validates: Requirements 2.3**
"""

from datetime import datetime, UTC

from sqlalchemy import Column, DateTime, String, Text
from sqlmodel import Field as SQLField
from sqlmodel import SQLModel

from my_api.shared.utils.ids import generate_ulid


class RoleBase(SQLModel):
    """Base role fields."""

    name: str = SQLField(
        min_length=1,
        max_length=100,
        description="Unique role name",
    )
    description: str | None = SQLField(
        default=None,
        max_length=500,
        description="Role description",
    )


class RoleDB(RoleBase, table=True):
    """Role database model."""

    __tablename__ = "roles"

    id: str = SQLField(
        default_factory=generate_ulid,
        primary_key=True,
        description="ULID identifier",
    )
    permissions: str = SQLField(
        default="",
        sa_column=Column(Text, nullable=False),
        description="Comma-separated permission list",
    )
    created_at: datetime = SQLField(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
        description="Creation timestamp",
    )
    updated_at: datetime = SQLField(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
        description="Last update timestamp",
    )

    def get_permissions_list(self) -> list[str]:
        """Get permissions as a list."""
        if not self.permissions:
            return []
        return [p.strip() for p in self.permissions.split(",") if p.strip()]

    def set_permissions_list(self, permissions: list[str]) -> None:
        """Set permissions from a list."""
        self.permissions = ",".join(permissions)


class UserRoleDB(SQLModel, table=True):
    """User-Role association table for many-to-many relationship."""

    __tablename__ = "user_roles"

    user_id: str = SQLField(
        sa_column=Column(String(26), primary_key=True),
        description="User ID",
    )
    role_id: str = SQLField(
        sa_column=Column(String(26), primary_key=True),
        description="Role ID",
    )
    assigned_at: datetime = SQLField(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
        description="When the role was assigned",
    )
    assigned_by: str | None = SQLField(
        default=None,
        max_length=26,
        description="ID of user who assigned this role",
    )


class RoleCreate(RoleBase):
    """DTO for creating roles."""

    permissions: list[str] = SQLField(
        default_factory=list,
        description="List of permission names",
    )


class RoleUpdate(SQLModel):
    """DTO for updating roles."""

    name: str | None = SQLField(default=None, min_length=1, max_length=100)
    description: str | None = SQLField(default=None, max_length=500)
    permissions: list[str] | None = SQLField(default=None)


class RoleResponse(RoleBase):
    """DTO for role responses."""

    id: str
    permissions: list[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_db(cls, db_role: RoleDB) -> "RoleResponse":
        """Create response from database model."""
        return cls(
            id=db_role.id,
            name=db_role.name,
            description=db_role.description,
            permissions=db_role.get_permissions_list(),
            created_at=db_role.created_at,
            updated_at=db_role.updated_at,
        )
