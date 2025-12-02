"""DTOs for ItemExample and PedidoExample.

Demonstrates:
- Pydantic v2 models with validation
- Create/Update/Response pattern
- Computed fields
- Field validators

**Feature: example-system-demo**
"""

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, field_validator, computed_field

from domain.examples.item_example import ItemExampleStatus


# === Money DTO ===


class MoneyDTO(BaseModel):
    """Money value object DTO."""

    amount: Decimal = Field(..., ge=0, description="Amount value")
    currency: str = Field(default="BRL", min_length=3, max_length=3)

    model_config = {"frozen": True}


# === ItemExample DTOs ===


class ItemExampleCreate(BaseModel):
    """DTO for creating an ItemExample."""

    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    sku: str = Field(..., min_length=1, max_length=50, pattern=r"^[A-Z0-9\-]+$")
    price: MoneyDTO
    quantity: int = Field(default=0, ge=0)
    category: str = Field(default="", max_length=100)
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("sku")
    @classmethod
    def uppercase_sku(cls, v: str) -> str:
        return v.upper()

    @field_validator("tags")
    @classmethod
    def lowercase_tags(cls, v: list[str]) -> list[str]:
        return [tag.lower().strip() for tag in v if tag.strip()]


class ItemExampleUpdate(BaseModel):
    """DTO for updating an ItemExample."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    price: MoneyDTO | None = None
    quantity: int | None = Field(default=None, ge=0)
    category: str | None = Field(default=None, max_length=100)
    tags: list[str] | None = None
    status: ItemExampleStatus | None = None


class ItemExampleResponse(BaseModel):
    """Response DTO for ItemExample."""

    id: str
    name: str
    description: str
    sku: str
    price: MoneyDTO
    quantity: int
    status: str
    category: str
    tags: list[str]
    is_available: bool
    total_value: MoneyDTO
    created_at: datetime
    updated_at: datetime
    created_by: str
    updated_by: str

    model_config = {"from_attributes": True}


class ItemExampleListResponse(BaseModel):
    """List response with summary."""

    items: list[ItemExampleResponse]
    total: int
    page: int
    page_size: int

    @computed_field
    @property
    def total_pages(self) -> int:
        if self.page_size == 0:
            return 1
        return (self.total + self.page_size - 1) // self.page_size

    @computed_field
    @property
    def has_next(self) -> bool:
        return self.page < self.total_pages


# === PedidoExample DTOs ===


class PedidoItemResponse(BaseModel):
    """Response DTO for order line item."""

    id: str
    item_id: str
    item_name: str
    quantity: int
    unit_price: MoneyDTO
    discount: Decimal
    subtotal: MoneyDTO
    total: MoneyDTO

    model_config = {"from_attributes": True}


class AddItemRequest(BaseModel):
    """Request to add item to order."""

    item_id: str = Field(..., min_length=1)
    quantity: int = Field(..., ge=1, le=9999)
    discount: Decimal = Field(default=Decimal("0"), ge=0, le=100)


class PedidoExampleCreate(BaseModel):
    """DTO for creating a PedidoExample."""

    customer_id: str = Field(..., min_length=1, max_length=100)
    customer_name: str = Field(..., min_length=1, max_length=200)
    customer_email: str = Field(default="", max_length=255)
    shipping_address: str = Field(default="", max_length=500)
    notes: str = Field(default="", max_length=2000)
    items: list[AddItemRequest] = Field(default_factory=list)

    @field_validator("customer_email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if v and "@" not in v:
            raise ValueError("Invalid email format")
        return v.lower().strip() if v else ""


class PedidoExampleUpdate(BaseModel):
    """DTO for updating a PedidoExample."""

    customer_name: str | None = Field(default=None, min_length=1, max_length=200)
    customer_email: str | None = Field(default=None, max_length=255)
    shipping_address: str | None = Field(default=None, max_length=500)
    notes: str | None = Field(default=None, max_length=2000)


class PedidoExampleResponse(BaseModel):
    """Response DTO for PedidoExample."""

    id: str
    customer_id: str
    customer_name: str
    customer_email: str
    status: str
    shipping_address: str
    notes: str
    items: list[PedidoItemResponse]
    items_count: int
    subtotal: MoneyDTO
    total_discount: MoneyDTO
    total: MoneyDTO
    can_be_modified: bool
    can_be_cancelled: bool
    created_at: datetime
    updated_at: datetime
    created_by: str
    updated_by: str

    model_config = {"from_attributes": True}


# === Action DTOs ===


class ConfirmPedidoRequest(BaseModel):
    """Request to confirm an order."""

    pass


class CancelPedidoRequest(BaseModel):
    """Request to cancel an order."""

    reason: str = Field(..., min_length=1, max_length=500)


class UpdateStatusRequest(BaseModel):
    """Request to update order status."""

    action: str = Field(..., pattern=r"^(process|ship|deliver)$")
