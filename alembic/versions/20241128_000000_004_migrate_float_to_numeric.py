"""Migrate price and tax columns from Float to Numeric.

Revision ID: 004
Revises: 003
Create Date: 2024-11-28 00:00:00

**Feature: alembic-migrations-refactoring**
**Validates: Requirements 3.1, 3.2, 3.3**

This migration changes the price and tax columns in the items table
from Float to Numeric(10,2) for proper monetary precision.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Migrate price and tax columns to Numeric type."""
    # Alter price column from Float to Numeric(10,2)
    op.alter_column(
        "items",
        "price",
        existing_type=sa.Float(),
        type_=sa.Numeric(precision=10, scale=2),
        existing_nullable=False,
        postgresql_using="price::numeric(10,2)",
    )

    # Alter tax column from Float to Numeric(10,2)
    op.alter_column(
        "items",
        "tax",
        existing_type=sa.Float(),
        type_=sa.Numeric(precision=10, scale=2),
        existing_nullable=True,
        postgresql_using="tax::numeric(10,2)",
    )


def downgrade() -> None:
    """Revert price and tax columns to Float type."""
    # Revert tax column to Float
    op.alter_column(
        "items",
        "tax",
        existing_type=sa.Numeric(precision=10, scale=2),
        type_=sa.Float(),
        existing_nullable=True,
    )

    # Revert price column to Float
    op.alter_column(
        "items",
        "price",
        existing_type=sa.Numeric(precision=10, scale=2),
        type_=sa.Float(),
        existing_nullable=False,
    )
