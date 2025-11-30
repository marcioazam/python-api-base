"""Add users table.

Revision ID: 001b
Revises: 001
Create Date: 2024-11-26 12:00:00

**Feature: alembic-migrations-refactoring**
**Validates: Requirements 4.1, 4.2**

This migration creates the users table required for foreign key
references in the user_roles table (migration 002).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001b"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create users table."""
    op.create_table(
        "users",
        sa.Column("id", sa.String(26), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    # Create index for email lookups
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    # Create index for active user queries
    op.create_index("ix_users_is_active", "users", ["is_active"])


def downgrade() -> None:
    """Drop users table."""
    op.drop_index("ix_users_is_active", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
