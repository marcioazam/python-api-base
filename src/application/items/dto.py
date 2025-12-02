"""DTOs for Items bounded context.

**Feature: domain-consolidation-2025**
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field


class ItemCreate(BaseModel):
    """DTO for creating a new Item."""

    name: str = Field(..., min_length=1, max_length=255, description="Item name")
    description: str | None = Field(
        None, max_length=1000, description="Item description"
    )
    price: float = Field(..., gt=0, description="Item price (must be positive)")
    tax: float | None = Field(None, ge=0, description="Tax amount")

    model_config = ConfigDict(extra="forbid")


class ItemUpdate(BaseModel):
    """DTO for updating an existing Item (all fields optional)."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)
    price: float | None = Field(None, gt=0)
    tax: float | None = Field(None, ge=0)

    model_config = ConfigDict(extra="forbid")


class ItemResponse(BaseModel):
    """DTO for Item API responses."""

    id: str
    name: str
    description: str | None = None
    price: float
    tax: float | None = None
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def price_with_tax(self) -> float:
        """Calculate price including tax."""
        return self.price + (self.tax or 0)

    model_config = ConfigDict(from_attributes=True)
