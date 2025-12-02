"""Add RBAC tables (roles, user_roles).

Revision ID: 002_rbac
Revises: 001b
Create Date: 2024-12-01 00:00:01

**Feature: core-rbac-system**
**Part of: Core API (permanent)**

Creates tables for Role-Based Access Control:
- roles: Role definitions with permissions
- user_roles: User-role assignments
"""

from typing import Sequence, Union
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002_rbac"
down_revision: Union[str, None] = "001b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create RBAC tables and seed default roles."""
    # === Roles Table ===
    op.create_table(
        "roles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(50), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True, default=""),
        sa.Column("permissions", sa.JSON(), nullable=False, default=[]),
        sa.Column("is_system", sa.Boolean(), nullable=False, default=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_index("ix_roles_name", "roles", ["name"], unique=True)
    op.create_index("ix_roles_active", "roles", ["is_active"])

    # === User Roles Table ===
    op.create_table(
        "user_roles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "role_id",
            sa.String(36),
            sa.ForeignKey("roles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("assigned_by", sa.String(36), nullable=True),
    )

    op.create_index("ix_user_roles_user_id", "user_roles", ["user_id"])
    op.create_index("ix_user_roles_role_id", "user_roles", ["role_id"])
    op.create_index(
        "ix_user_roles_unique",
        "user_roles",
        ["user_id", "role_id"],
        unique=True,
    )

    # === Seed Default Roles ===
    from datetime import datetime, UTC

    now = datetime.now(UTC)

    op.execute(
        sa.text(
            """
            INSERT INTO roles (id, name, description, permissions, is_system, is_active, created_at, updated_at)
            VALUES
            (:admin_id, 'admin', 'Full system administrator', :admin_perms, true, true, :now, :now),
            (:user_id, 'user', 'Standard user with read/write access', :user_perms, true, true, :now, :now),
            (:viewer_id, 'viewer', 'Read-only access', :viewer_perms, true, true, :now, :now),
            (:moderator_id, 'moderator', 'Content moderator', :moderator_perms, true, true, :now, :now)
            """
        ).bindparams(
            admin_id=str(uuid4()),
            user_id=str(uuid4()),
            viewer_id=str(uuid4()),
            moderator_id=str(uuid4()),
            admin_perms='["read", "write", "delete", "admin", "manage_users", "manage_roles", "view_audit", "export_data"]',
            user_perms='["read", "write"]',
            viewer_perms='["read"]',
            moderator_perms='["read", "write", "delete", "view_audit"]',
            now=now,
        )
    )


def downgrade() -> None:
    """Drop RBAC tables."""
    op.drop_index("ix_user_roles_unique", table_name="user_roles")
    op.drop_index("ix_user_roles_role_id", table_name="user_roles")
    op.drop_index("ix_user_roles_user_id", table_name="user_roles")
    op.drop_table("user_roles")

    op.drop_index("ix_roles_active", table_name="roles")
    op.drop_index("ix_roles_name", table_name="roles")
    op.drop_table("roles")
