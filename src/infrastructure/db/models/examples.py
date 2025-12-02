"""SQLModel models for ItemExample and PedidoExample.

Demonstrates:
- SQLModel integration
- Relationship mapping
- Soft delete support
- Audit fields

**Feature: example-system-demo**
"""

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, JSON, Text

from core.shared.utils.datetime import utc_now


class ItemExampleModel(SQLModel, table=True):
    """Database model for ItemExample."""

    __tablename__ = "item_examples"

    id: str = Field(primary_key=True)
    name: str = Field(max_length=200, index=True)
    description: str = Field(default="", sa_column=Column(Text))
    sku: str = Field(max_length=50, unique=True, index=True)
    price_amount: Decimal = Field(default=Decimal("0"), decimal_places=2)
    price_currency: str = Field(default="BRL", max_length=3)
    quantity: int = Field(default=0, ge=0)
    status: str = Field(default="active", max_length=20, index=True)
    category: str = Field(default="", max_length=100, index=True)
    tags: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    metadata: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))

    # Audit fields
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    created_by: str = Field(default="system", max_length=100)
    updated_by: str = Field(default="system", max_length=100)

    # Soft delete
    is_deleted: bool = Field(default=False, index=True)
    deleted_at: datetime | None = Field(default=None)

    # Relationships
    pedido_items: list["PedidoItemExampleModel"] = Relationship(
        back_populates="item"
    )


class PedidoExampleModel(SQLModel, table=True):
    """Database model for PedidoExample."""

    __tablename__ = "pedido_examples"

    id: str = Field(primary_key=True)
    customer_id: str = Field(max_length=100, index=True)
    customer_name: str = Field(max_length=200)
    customer_email: str = Field(default="", max_length=255)
    status: str = Field(default="pending", max_length=20, index=True)
    shipping_address: str = Field(default="", max_length=500)
    notes: str = Field(default="", sa_column=Column(Text))
    tenant_id: str | None = Field(default=None, max_length=100, index=True)
    metadata: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))

    # Audit fields
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    created_by: str = Field(default="system", max_length=100)
    updated_by: str = Field(default="system", max_length=100)

    # Soft delete
    is_deleted: bool = Field(default=False, index=True)
    deleted_at: datetime | None = Field(default=None)

    # Relationships
    items: list["PedidoItemExampleModel"] = Relationship(
        back_populates="pedido",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class PedidoItemExampleModel(SQLModel, table=True):
    """Database model for order line items."""

    __tablename__ = "pedido_item_examples"

    id: str = Field(primary_key=True)
    pedido_id: str = Field(foreign_key="pedido_examples.id", index=True)
    item_id: str = Field(foreign_key="item_examples.id", index=True)
    item_name: str = Field(max_length=200)
    quantity: int = Field(ge=1)
    unit_price_amount: Decimal = Field(decimal_places=2)
    unit_price_currency: str = Field(default="BRL", max_length=3)
    discount: Decimal = Field(default=Decimal("0"), decimal_places=2)

    # Relationships
    pedido: PedidoExampleModel = Relationship(back_populates="items")
    item: ItemExampleModel = Relationship(back_populates="pedido_items")
