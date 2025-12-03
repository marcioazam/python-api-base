"""ItemExample entity with value objects and domain events.

Demonstrates:
- BaseEntity[IdType] with PEP 695 generics
- Value Objects (Money)
- Domain Events
- Soft delete support
- Audit fields

**Feature: example-system-demo**
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import Field, PrivateAttr

from core.base.domain.entity import AuditableEntity
from core.base.events.domain_event import DomainEvent
from core.shared.utils.datetime import utc_now


# === Value Objects ===


@dataclass(frozen=True, slots=True)
class Money:
    """Value object for monetary amounts.

    Immutable, comparable, and supports arithmetic operations.
    """

    amount: Decimal
    currency: str = "BRL"

    def __post_init__(self) -> None:
        if self.amount < 0:
            raise ValueError("Amount cannot be negative")
        if len(self.currency) != 3:
            raise ValueError("Currency must be 3-letter ISO code")

    def __add__(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise ValueError("Cannot add different currencies")
        return Money(self.amount + other.amount, self.currency)

    def __mul__(self, quantity: int) -> "Money":
        return Money(self.amount * quantity, self.currency)

    def to_dict(self) -> dict[str, Any]:
        return {"amount": str(self.amount), "currency": self.currency}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Money":
        return cls(Decimal(data["amount"]), data.get("currency", "BRL"))


# === Enums ===


class ItemExampleStatus(Enum):
    """Item status enumeration."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    OUT_OF_STOCK = "out_of_stock"
    DISCONTINUED = "discontinued"


# === Domain Events ===


@dataclass(frozen=True, kw_only=True)
class ItemExampleCreated(DomainEvent):
    """Event raised when an ItemExample is created."""

    item_id: str
    name: str
    price_amount: Decimal
    occurred_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True, kw_only=True)
class ItemExampleUpdated(DomainEvent):
    """Event raised when an ItemExample is updated."""

    item_id: str
    changes: dict[str, Any]
    occurred_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True, kw_only=True)
class ItemExampleDeleted(DomainEvent):
    """Event raised when an ItemExample is soft-deleted."""

    item_id: str
    occurred_at: datetime = field(default_factory=utc_now)


# === Entity ===


class ItemExample(AuditableEntity[str]):
    """ItemExample aggregate root.

    Demonstrates:
    - PEP 695 generic entity (inherits AuditableEntity[str])
    - Value objects (Money)
    - Domain events
    - Status transitions
    - Soft delete

    Example:
        >>> item = ItemExample.create(
        ...     name="Widget",
        ...     description="A useful widget",
        ...     price=Money(Decimal("99.90")),
        ...     sku="WDG-001",
        ... )
        >>> item.events  # Contains ItemExampleCreated event
    """

    name: str = ""
    description: str = ""
    sku: str = ""
    price: Money = Field(default_factory=lambda: Money(Decimal("0")))
    quantity: int = 0
    status: ItemExampleStatus = ItemExampleStatus.ACTIVE
    category: str = ""
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    # Domain events queue
    _events: list[DomainEvent] = PrivateAttr(default_factory=list)

    @classmethod
    def create(
        cls,
        name: str,
        description: str,
        price: Money,
        sku: str,
        quantity: int = 0,
        category: str = "",
        tags: list[str] | None = None,
        created_by: str = "system",
    ) -> "ItemExample":
        """Factory method to create a new ItemExample with events."""
        from uuid import uuid4

        item = cls(
            id=str(uuid4()),
            name=name,
            description=description,
            sku=sku,
            price=price,
            quantity=quantity,
            category=category,
            tags=tags or [],
            created_by=created_by,
            updated_by=created_by,
        )
        item._events.append(
            ItemExampleCreated(
                item_id=item.id,
                name=name,
                price_amount=price.amount,
            )
        )
        return item

    def update(
        self,
        name: str | None = None,
        description: str | None = None,
        price: Money | None = None,
        quantity: int | None = None,
        category: str | None = None,
        updated_by: str = "system",
    ) -> None:
        """Update item fields with change tracking."""
        changes: dict[str, Any] = {}

        if name is not None and name != self.name:
            changes["name"] = {"old": self.name, "new": name}
            self.name = name

        if description is not None and description != self.description:
            changes["description"] = {"old": self.description, "new": description}
            self.description = description

        if price is not None and price != self.price:
            changes["price"] = {"old": self.price.to_dict(), "new": price.to_dict()}
            self.price = price

        if quantity is not None and quantity != self.quantity:
            changes["quantity"] = {"old": self.quantity, "new": quantity}
            self.quantity = quantity
            self._update_status_from_quantity()

        if category is not None and category != self.category:
            changes["category"] = {"old": self.category, "new": category}
            self.category = category

        if changes:
            self.mark_updated_by(updated_by)
            self._events.append(ItemExampleUpdated(item_id=self.id, changes=changes))

    def _update_status_from_quantity(self) -> None:
        """Update status based on quantity."""
        if self.quantity <= 0 and self.status == ItemExampleStatus.ACTIVE:
            self.status = ItemExampleStatus.OUT_OF_STOCK
        elif self.quantity > 0 and self.status == ItemExampleStatus.OUT_OF_STOCK:
            self.status = ItemExampleStatus.ACTIVE

    def deactivate(self, updated_by: str = "system") -> None:
        """Deactivate the item."""
        self.status = ItemExampleStatus.INACTIVE
        self.mark_updated_by(updated_by)

    def discontinue(self, updated_by: str = "system") -> None:
        """Discontinue the item."""
        self.status = ItemExampleStatus.DISCONTINUED
        self.mark_updated_by(updated_by)

    def soft_delete(self, deleted_by: str = "system") -> None:
        """Soft delete with event."""
        self.mark_deleted()
        self.mark_updated_by(deleted_by)
        self._events.append(ItemExampleDeleted(item_id=self.id))

    @property
    def events(self) -> list[DomainEvent]:
        """Get pending domain events."""
        return self._events.copy()

    def clear_events(self) -> None:
        """Clear pending domain events after publishing."""
        self._events.clear()

    @property
    def is_available(self) -> bool:
        """Check if item is available for ordering."""
        return (
            self.status == ItemExampleStatus.ACTIVE
            and self.quantity > 0
            and not self.is_deleted
        )

    @property
    def total_value(self) -> Money:
        """Calculate total inventory value."""
        return self.price * self.quantity
