"""Add roles and user_roles tables.

Revision ID: 002
Revises: 001
Create Date: 2024-11-27 00:00:01

**Feature: api-base-improvements**
**Validates: Requirements 2.3**
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create roles and user_roles tables."""
    # Create roles table
    op.create_table(
        "roles",
        sa.Column("id", sa.String(26), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("permissions", sa.Text(), nullable=False, default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    # Create index on role name for fast lookups
    op.create_index("ix_roles_name", "roles", ["name"])

    # Create user_roles association table
    op.create_table(
        "user_roles",
        sa.Column(
            "user_id",
            sa.String(26),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "role_id",
            sa.String(26),
            sa.ForeignKey("roles.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("assigned_at", sa.DateTime(), nullable=False),
        sa.Column("assigned_by", sa.String(26), nullable=True),
    )

    # Create indexes for efficient queries
    op.create_index("ix_user_roles_user_id", "user_roles", ["user_id"])
    op.create_index("ix_user_roles_role_id", "user_roles", ["role_id"])


def downgrade() -> None:
    """Drop roles and user_roles tables."""
    op.drop_index("ix_user_roles_role_id", table_name="user_roles")
    op.drop_index("ix_user_roles_user_id", table_name="user_roles")
    op.drop_table("user_roles")

    op.drop_index("ix_roles_name", table_name="roles")
    op.drop_table("roles")
