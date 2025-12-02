"""Specifications for ItemExample and PedidoExample.

Demonstrates:
- Specification[T] pattern with PEP 695 generics
- Composable specifications with &, |, ~ operators
- Business rule encapsulation

**Feature: example-system-demo**
"""

from decimal import Decimal

from core.base.specification import Specification
from domain.examples.item_example import ItemExample, ItemExampleStatus, Money
from domain.examples.pedido_example import PedidoExample, PedidoStatus


# === ItemExample Specifications ===


class ItemExampleActiveSpec(Specification[ItemExample]):
    """Specification for active items."""

    def is_satisfied_by(self, candidate: ItemExample) -> bool:
        return (
            candidate.status == ItemExampleStatus.ACTIVE
            and not candidate.is_deleted
        )


class ItemExampleInStockSpec(Specification[ItemExample]):
    """Specification for items with available stock."""

    def is_satisfied_by(self, candidate: ItemExample) -> bool:
        return candidate.quantity > 0


class ItemExamplePriceRangeSpec(Specification[ItemExample]):
    """Specification for items within a price range."""

    def __init__(self, min_price: Decimal, max_price: Decimal) -> None:
        self.min_price = min_price
        self.max_price = max_price

    def is_satisfied_by(self, candidate: ItemExample) -> bool:
        return self.min_price <= candidate.price.amount <= self.max_price


class ItemExampleCategorySpec(Specification[ItemExample]):
    """Specification for items in a specific category."""

    def __init__(self, category: str) -> None:
        self.category = category

    def is_satisfied_by(self, candidate: ItemExample) -> bool:
        return candidate.category == self.category


class ItemExampleAvailableSpec(Specification[ItemExample]):
    """Composite specification for available items.

    Item must be:
    - Active status
    - Not deleted
    - Has stock > 0
    """

    def is_satisfied_by(self, candidate: ItemExample) -> bool:
        return candidate.is_available


class ItemExampleTagSpec(Specification[ItemExample]):
    """Specification for items with specific tag."""

    def __init__(self, tag: str) -> None:
        self.tag = tag

    def is_satisfied_by(self, candidate: ItemExample) -> bool:
        return self.tag in candidate.tags


# === PedidoExample Specifications ===


class PedidoPendingSpec(Specification[PedidoExample]):
    """Specification for pending orders."""

    def is_satisfied_by(self, candidate: PedidoExample) -> bool:
        return candidate.status == PedidoStatus.PENDING


class PedidoConfirmedSpec(Specification[PedidoExample]):
    """Specification for confirmed orders."""

    def is_satisfied_by(self, candidate: PedidoExample) -> bool:
        return candidate.status == PedidoStatus.CONFIRMED


class PedidoMinValueSpec(Specification[PedidoExample]):
    """Specification for orders with minimum value."""

    def __init__(self, min_value: Decimal) -> None:
        self.min_value = min_value

    def is_satisfied_by(self, candidate: PedidoExample) -> bool:
        return candidate.total.amount >= self.min_value


class PedidoCustomerSpec(Specification[PedidoExample]):
    """Specification for orders from a specific customer."""

    def __init__(self, customer_id: str) -> None:
        self.customer_id = customer_id

    def is_satisfied_by(self, candidate: PedidoExample) -> bool:
        return candidate.customer_id == self.customer_id


class PedidoHasItemsSpec(Specification[PedidoExample]):
    """Specification for orders that have items."""

    def is_satisfied_by(self, candidate: PedidoExample) -> bool:
        return len(candidate.items) > 0


class PedidoMinItemsSpec(Specification[PedidoExample]):
    """Specification for orders with minimum number of items."""

    def __init__(self, min_items: int) -> None:
        self.min_items = min_items

    def is_satisfied_by(self, candidate: PedidoExample) -> bool:
        return candidate.items_count >= self.min_items


class PedidoTenantSpec(Specification[PedidoExample]):
    """Specification for tenant isolation."""

    def __init__(self, tenant_id: str) -> None:
        self.tenant_id = tenant_id

    def is_satisfied_by(self, candidate: PedidoExample) -> bool:
        return candidate.tenant_id == self.tenant_id


# === Composite Specification Examples ===


def available_items_in_category(category: str) -> Specification[ItemExample]:
    """Create composite spec for available items in category.

    Example of using & operator:
        >>> spec = available_items_in_category("electronics")
        >>> for item in items:
        ...     if spec.is_satisfied_by(item):
        ...         print(item.name)
    """
    return ItemExampleAvailableSpec() & ItemExampleCategorySpec(category)


def high_value_pending_orders(min_value: Decimal) -> Specification[PedidoExample]:
    """Create composite spec for high-value pending orders.

    Example of using & operator:
        >>> spec = high_value_pending_orders(Decimal("1000"))
        >>> priority_orders = [o for o in orders if spec.is_satisfied_by(o)]
    """
    return PedidoPendingSpec() & PedidoMinValueSpec(min_value)


def orders_ready_for_processing() -> Specification[PedidoExample]:
    """Create spec for orders ready to process.

    Must be confirmed and have items.
    """
    return PedidoConfirmedSpec() & PedidoHasItemsSpec()
