"""Item domain entity.

This module defines the Item entity and its related DTOs.

**Feature: domain-code-review-fixes**
**Validates: Requirements 2.1, 2.2**
"""

from datetime import datetime, UTC
from typing import Optional

from pydantic import ConfigDict
from sqlalchemy import Column, DateTime, Float, String, Text
from sqlmodel import Field as SQLField
from sqlmodel import SQLModel

from my_app.shared.utils.ids import generate_ulid


class ItemBase(SQLModel):
    """Base Item model with common fields."""

    name: str = SQLField(..., min_length=1, max_length=255, description="Item name")
    description: Optional[str] = SQLField(None, max_length=1000, description="Item description")
    price: float = SQLField(..., ge=0, description="Item price")
    tax: Optional[float] = SQLField(None, ge=0, description="Item tax")


class ItemCreate(ItemBase):
    """DTO for creating a new Item."""

    model_config = ConfigDict(extra="forbid")


class ItemUpdate(SQLModel):
    """DTO for updating an existing Item."""

    name: Optional[str] = SQLField(None, min_length=1, max_length=255)
    description: Optional[str] = SQLField(None, max_length=1000)
    price: Optional[float] = SQLField(None, ge=0)
    tax: Optional[float] = SQLField(None, ge=0)

    model_config = ConfigDict(extra="forbid")


class Item(ItemBase, table=True):
    """Item database model."""

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
    description: Optional[str] = SQLField(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="Item description",
    )
    price: float = SQLField(
        sa_column=Column(Float, nullable=False),
        description="Item price",
    )
    tax: Optional[float] = SQLField(
        default=None,
        sa_column=Column(Float, nullable=True),
        description="Item tax",
    )
    created_at: datetime = SQLField(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
        description="Record creation timestamp",
    )
    updated_at: Optional[datetime] = SQLField(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
        description="Record update timestamp",
    )


class ItemResponse(ItemBase):
    """DTO for Item API responses."""

    id: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
