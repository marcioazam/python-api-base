"""Item domain entity.

Note: SQLModel entities use SQLField for validation constraints.
For pure Pydantic models (non-database), use Annotated types from
my_api.shared.types for cleaner inline validation.
"""

from datetime import datetime, UTC

from pydantic import computed_field
from sqlalchemy import Column, DateTime
from sqlmodel import Field as SQLField
from sqlmodel import SQLModel

from my_api.shared.utils.ids import generate_ulid


class ItemBase(SQLModel):
    """Base item fields shared between create/update/response."""

    name: str = SQLField(min_length=1, max_length=255, description="Item name")
    description: str | None = SQLField(
        default=None, max_length=1000, description="Item description"
    )
    price: float = SQLField(gt=0, description="Item price (must be positive)")
    tax: float | None = SQLField(default=None, ge=0, description="Tax amount")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "Premium Widget",
                    "description": "A high-quality widget for all your needs",
                    "price": 29.99,
                    "tax": 2.40,
                }
            ]
        }
    }


class Item(ItemBase, table=True):
    """Item database model."""

    __tablename__ = "items"

    id: str = SQLField(
        default_factory=generate_ulid,
        primary_key=True,
        description="ULID identifier",
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
    is_deleted: bool = SQLField(default=False, description="Soft delete flag")


class ItemCreate(ItemBase):
    """DTO for creating items."""

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "New Product",
                    "description": "A brand new product",
                    "price": 19.99,
                    "tax": 1.60,
                }
            ]
        }
    }


class ItemUpdate(SQLModel):
    """DTO for updating items (all fields optional)."""

    name: str | None = SQLField(default=None, min_length=1, max_length=255)
    description: str | None = SQLField(default=None, max_length=1000)
    price: float | None = SQLField(default=None, gt=0)
    tax: float | None = SQLField(default=None, ge=0)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "Updated Product Name",
                    "price": 24.99,
                }
            ]
        }
    }


class ItemResponse(ItemBase):
    """DTO for item responses."""

    id: str
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def price_with_tax(self) -> float:
        """Calculate price including tax."""
        return self.price + (self.tax or 0)

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [
                {
                    "id": "01HXYZ123456789ABCDEFGHIJK",
                    "name": "Premium Widget",
                    "description": "A high-quality widget for all your needs",
                    "price": 29.99,
                    "tax": 2.40,
                    "created_at": "2024-01-15T10:30:00Z",
                    "updated_at": "2024-01-15T10:30:00Z",
                    "price_with_tax": 32.39,
                }
            ]
        },
    }
