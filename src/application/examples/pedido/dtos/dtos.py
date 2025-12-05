"""DTOs for PedidoExample.

Demonstrates:
- Pydantic v2 models with validation
- Create/Update/Response pattern
- Field validators

**Feature: example-system-demo**
"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from application.examples.shared.dtos import MoneyDTO


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


class ConfirmPedidoRequest(BaseModel):
    """Request to confirm an order."""


class CancelPedidoRequest(BaseModel):
    """Request to cancel an order."""

    reason: str = Field(..., min_length=1, max_length=500)


class UpdateStatusRequest(BaseModel):
    """Request to update order status."""

    action: str = Field(..., pattern=r"^(process|ship|deliver)$")
