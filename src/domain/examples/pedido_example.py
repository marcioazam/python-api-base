"""PedidoExample aggregate with order items.

Demonstrates:
- Aggregate Root pattern
- Entity relationships (Pedido -> PedidoItems)
- Business rules validation
- Domain events for state transitions
- Value calculations

**Feature: example-system-demo**
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import Field, PrivateAttr

from core.base.entity import AuditableEntity
from core.base.domain_event import DomainEvent
from core.shared.utils.datetime import utc_now
from domain.examples.item_example import Money


# === Enums ===


class PedidoStatus(Enum):
    """Order status enumeration."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


# === Domain Events ===


@dataclass(frozen=True, kw_only=True)
class PedidoCreated(DomainEvent):
    """Event raised when a PedidoExample is created."""

    pedido_id: str
    customer_id: str
    occurred_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True, kw_only=True)
class PedidoItemAdded(DomainEvent):
    """Event raised when an item is added to order."""

    pedido_id: str
    item_id: str
    quantity: int
    unit_price: Decimal
    occurred_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True, kw_only=True)
class PedidoCompleted(DomainEvent):
    """Event raised when order is completed."""

    pedido_id: str
    total: Decimal
    items_count: int
    occurred_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True, kw_only=True)
class PedidoCancelled(DomainEvent):
    """Event raised when order is cancelled."""

    pedido_id: str
    reason: str
    occurred_at: datetime = field(default_factory=utc_now)


# === Entities ===


@dataclass
class PedidoItemExample:
    """Order line item entity.

    Represents an item within an order with quantity and pricing.
    """

    id: str
    pedido_id: str
    item_id: str
    item_name: str
    quantity: int
    unit_price: Money
    discount: Decimal = Decimal("0")

    @classmethod
    def create(
        cls,
        pedido_id: str,
        item_id: str,
        item_name: str,
        quantity: int,
        unit_price: Money,
        discount: Decimal = Decimal("0"),
    ) -> "PedidoItemExample":
        """Factory method to create order item."""
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        if discount < 0 or discount > 100:
            raise ValueError("Discount must be between 0 and 100")

        return cls(
            id=str(uuid4()),
            pedido_id=pedido_id,
            item_id=item_id,
            item_name=item_name,
            quantity=quantity,
            unit_price=unit_price,
            discount=discount,
        )

    @property
    def subtotal(self) -> Money:
        """Calculate line item subtotal before discount."""
        return self.unit_price * self.quantity

    @property
    def discount_amount(self) -> Money:
        """Calculate discount amount."""
        discount_value = self.subtotal.amount * (self.discount / 100)
        return Money(discount_value, self.unit_price.currency)

    @property
    def total(self) -> Money:
        """Calculate line item total after discount."""
        return Money(
            self.subtotal.amount - self.discount_amount.amount,
            self.unit_price.currency,
        )


class PedidoExample(AuditableEntity[str]):
    """PedidoExample aggregate root.

    Demonstrates:
    - Aggregate root with child entities
    - Business rules enforcement
    - Domain events
    - Status state machine
    - Value calculations

    Example:
        >>> pedido = PedidoExample.create(
        ...     customer_id="cust-123",
        ...     customer_name="John Doe",
        ... )
        >>> pedido.add_item(item_id="item-1", name="Widget", qty=2, price=Money(Decimal("50")))
        >>> pedido.confirm()
    """

    customer_id: str = ""
    customer_name: str = ""
    customer_email: str = ""
    status: PedidoStatus = PedidoStatus.PENDING
    items: list[PedidoItemExample] = Field(default_factory=list)
    notes: str = ""
    shipping_address: str = ""
    tenant_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    # Domain events queue
    _events: list[DomainEvent] = PrivateAttr(default_factory=list)

    @classmethod
    def create(
        cls,
        customer_id: str,
        customer_name: str,
        customer_email: str = "",
        shipping_address: str = "",
        notes: str = "",
        tenant_id: str | None = None,
        created_by: str = "system",
    ) -> "PedidoExample":
        """Factory method to create a new order."""
        pedido = cls(
            id=str(uuid4()),
            customer_id=customer_id,
            customer_name=customer_name,
            customer_email=customer_email,
            shipping_address=shipping_address,
            notes=notes,
            tenant_id=tenant_id,
            created_by=created_by,
            updated_by=created_by,
        )
        pedido._events.append(
            PedidoCreated(pedido_id=pedido.id, customer_id=customer_id)
        )
        return pedido

    def add_item(
        self,
        item_id: str,
        item_name: str,
        quantity: int,
        unit_price: Money,
        discount: Decimal = Decimal("0"),
    ) -> PedidoItemExample:
        """Add an item to the order.

        Raises:
            ValueError: If order is not in PENDING status.
        """
        if self.status != PedidoStatus.PENDING:
            raise ValueError(f"Cannot add items to order in {self.status.value} status")

        # Check if item already exists
        existing = next((i for i in self.items if i.item_id == item_id), None)
        if existing:
            existing.quantity += quantity
            item = existing
        else:
            item = PedidoItemExample.create(
                pedido_id=self.id,
                item_id=item_id,
                item_name=item_name,
                quantity=quantity,
                unit_price=unit_price,
                discount=discount,
            )
            self.items.append(item)

        self._events.append(
            PedidoItemAdded(
                pedido_id=self.id,
                item_id=item_id,
                quantity=quantity,
                unit_price=unit_price.amount,
            )
        )
        self.mark_updated()
        return item

    def remove_item(self, item_id: str) -> bool:
        """Remove an item from the order."""
        if self.status != PedidoStatus.PENDING:
            raise ValueError(f"Cannot remove items from order in {self.status.value} status")

        original_count = len(self.items)
        self.items = [i for i in self.items if i.item_id != item_id]

        if len(self.items) < original_count:
            self.mark_updated()
            return True
        return False

    def confirm(self, updated_by: str = "system") -> None:
        """Confirm the order."""
        if not self.items:
            raise ValueError("Cannot confirm order without items")
        if self.status != PedidoStatus.PENDING:
            raise ValueError(f"Cannot confirm order in {self.status.value} status")

        self.status = PedidoStatus.CONFIRMED
        self.mark_updated_by(updated_by)
        self._events.append(
            PedidoCompleted(
                pedido_id=self.id,
                total=self.total.amount,
                items_count=len(self.items),
            )
        )

    def process(self, updated_by: str = "system") -> None:
        """Start processing the order."""
        if self.status != PedidoStatus.CONFIRMED:
            raise ValueError(f"Cannot process order in {self.status.value} status")
        self.status = PedidoStatus.PROCESSING
        self.mark_updated_by(updated_by)

    def ship(self, updated_by: str = "system") -> None:
        """Mark order as shipped."""
        if self.status != PedidoStatus.PROCESSING:
            raise ValueError(f"Cannot ship order in {self.status.value} status")
        self.status = PedidoStatus.SHIPPED
        self.mark_updated_by(updated_by)

    def deliver(self, updated_by: str = "system") -> None:
        """Mark order as delivered."""
        if self.status != PedidoStatus.SHIPPED:
            raise ValueError(f"Cannot deliver order in {self.status.value} status")
        self.status = PedidoStatus.DELIVERED
        self.mark_updated_by(updated_by)

    def cancel(self, reason: str, updated_by: str = "system") -> None:
        """Cancel the order."""
        if self.status in (PedidoStatus.DELIVERED, PedidoStatus.CANCELLED):
            raise ValueError(f"Cannot cancel order in {self.status.value} status")

        self.status = PedidoStatus.CANCELLED
        self.mark_updated_by(updated_by)
        self._events.append(PedidoCancelled(pedido_id=self.id, reason=reason))

    @property
    def subtotal(self) -> Money:
        """Calculate order subtotal before discounts."""
        if not self.items:
            return Money(Decimal("0"))
        total = Decimal("0")
        currency = self.items[0].unit_price.currency if self.items else "BRL"
        for item in self.items:
            total += item.subtotal.amount
        return Money(total, currency)

    @property
    def total_discount(self) -> Money:
        """Calculate total discount amount."""
        if not self.items:
            return Money(Decimal("0"))
        total = Decimal("0")
        currency = self.items[0].unit_price.currency if self.items else "BRL"
        for item in self.items:
            total += item.discount_amount.amount
        return Money(total, currency)

    @property
    def total(self) -> Money:
        """Calculate order total after discounts."""
        if not self.items:
            return Money(Decimal("0"))
        total = Decimal("0")
        currency = self.items[0].unit_price.currency if self.items else "BRL"
        for item in self.items:
            total += item.total.amount
        return Money(total, currency)

    @property
    def items_count(self) -> int:
        """Get total quantity of items."""
        return sum(item.quantity for item in self.items)

    @property
    def events(self) -> list[DomainEvent]:
        """Get pending domain events."""
        return self._events.copy()

    def clear_events(self) -> None:
        """Clear pending domain events after publishing."""
        self._events.clear()

    @property
    def can_be_modified(self) -> bool:
        """Check if order can be modified."""
        return self.status == PedidoStatus.PENDING

    @property
    def can_be_cancelled(self) -> bool:
        """Check if order can be cancelled."""
        return self.status not in (PedidoStatus.DELIVERED, PedidoStatus.CANCELLED)
