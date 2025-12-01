"""Item ORM model for database persistence.

**Feature: domain-consolidation-2025**
"""

from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Float, String, Text
from sqlmodel import Field as SQLField
from sqlmodel import SQLModel

from core.shared.utils.ids import generate_ulid


class ItemModel(SQLModel, table=True):
    """Item database model (ORM).

    This is the persistence model - separate from domain entities.
    """

    __tablename__ = "items"

    id: str = SQLField(
        default_factory=generate_ulid,
        primary_key=True,
        description="ULID identifier",
    )
    name: str = SQLField(
        sa_column=Column(String(255), nullable=False),
        description="Item name",
    )
    description: str | None = SQLField(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="Item description",
    )
    price: float = SQLField(
        sa_column=Column(Float, nullable=False),
        description="Item price",
    )
    tax: float | None = SQLField(
        default=None,
        sa_column=Column(Float, nullable=True),
        description="Item tax",
    )
    created_at: datetime = SQLField(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
        description="Record creation timestamp",
    )
    updated_at: datetime = SQLField(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
        description="Record update timestamp",
    )
    is_deleted: bool = SQLField(default=False, description="Soft delete flag")
