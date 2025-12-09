"""DTOs for Order use cases.

**Feature: architecture-consolidation-2025**
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class OrderItemInput:
    """Input for a single order item."""

    item_id: str
    quantity: int
    unit_price: Decimal | None = None  # If None, will be fetched from catalog


@dataclass(frozen=True)
class PlaceOrderInput:
    """Input for PlaceOrderUseCase.

    Contains all data needed to place an order.
    """

    customer_id: str
    items: list[OrderItemInput]
    shipping_address: str
    payment_method: str = "credit_card"
    notes: str = ""


@dataclass(frozen=True)
class OrderItemOutput:
    """Output for a single order item."""

    item_id: str
    item_name: str
    quantity: int
    unit_price: Decimal
    total_price: Decimal


@dataclass(frozen=True)
class PlaceOrderOutput:
    """Output from PlaceOrderUseCase.

    Contains the created order details.
    """

    order_id: str
    customer_id: str
    items: list[OrderItemOutput]
    subtotal: Decimal
    shipping_cost: Decimal
    total: Decimal
    status: str
    estimated_delivery: datetime
    created_at: datetime
