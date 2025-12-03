"""Specifications for PedidoExample.

Demonstrates:
- Specification[T] pattern with PEP 695 generics
- Composable specifications with &, |, ~ operators
- Business rule encapsulation

**Feature: example-system-demo**
"""

from decimal import Decimal

from core.base.patterns.specification import Specification
from domain.examples.pedido.entity import PedidoExample, PedidoStatus


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


def high_value_pending_orders(min_value: Decimal) -> Specification[PedidoExample]:
    """Create composite spec for high-value pending orders."""
    return PedidoPendingSpec() & PedidoMinValueSpec(min_value)


def orders_ready_for_processing() -> Specification[PedidoExample]:
    """Create spec for orders ready to process.

    Example:
        >>> ready_orders = orders_ready_for_processing()
        >>> orders = repository.find_all(ready_orders)
        >>> for order in orders:
        ...     process_order(order)
    """
    return PedidoConfirmedSpec() & PedidoHasItemsSpec()


def vip_customer_orders(
    customer_id: str, min_value: Decimal = Decimal("1000.00")
) -> Specification[PedidoExample]:
    """Create composite spec for VIP customer high-value orders.

    Useful for:
    - Priority processing
    - Special handling
    - Loyalty program rewards

    Example:
        >>> vip_orders = vip_customer_orders("customer-123", Decimal("5000.00"))
        >>> for order in repository.find_all(vip_orders):
        ...     assign_priority_shipping(order)
        ...     send_vip_notification(order.customer_id)
    """
    return (
        PedidoCustomerSpec(customer_id)
        & PedidoMinValueSpec(min_value)
        & PedidoConfirmedSpec()
    )


def bulk_orders(min_items: int = 10) -> Specification[PedidoExample]:
    """Create composite spec for bulk orders.

    Bulk orders have many items and may qualify for:
    - Volume discounts
    - Special shipping arrangements
    - Inventory allocation priority

    Example:
        >>> bulk = bulk_orders(min_items=20)
        >>> confirmed_bulk = bulk & PedidoConfirmedSpec()
        >>> for order in repository.find_all(confirmed_bulk):
        ...     apply_bulk_discount(order)
    """
    return PedidoMinItemsSpec(min_items) & PedidoHasItemsSpec()


def processable_high_value_orders(
    min_value: Decimal = Decimal("500.00")
) -> Specification[PedidoExample]:
    """Create composite spec for high-value orders ready for processing.

    Combines readiness criteria with value threshold.

    Example:
        >>> high_value_ready = processable_high_value_orders(Decimal("1000.00"))
        >>> priority_orders = repository.find_all(high_value_ready)
        >>> # Process these orders first
    """
    return orders_ready_for_processing() & PedidoMinValueSpec(min_value)


def multi_tenant_query(
    tenant_id: str, status: PedidoStatus
) -> Specification[PedidoExample]:
    """Create composite spec for tenant-isolated orders with specific status.

    Essential for multi-tenant SaaS applications.

    Example:
        >>> tenant_pending = multi_tenant_query("tenant-abc", PedidoStatus.PENDING)
        >>> tenant_orders = repository.find_all(tenant_pending)
        >>> # Only returns orders for tenant-abc with PENDING status
    """
    if status == PedidoStatus.PENDING:
        status_spec = PedidoPendingSpec()
    elif status == PedidoStatus.CONFIRMED:
        status_spec = PedidoConfirmedSpec()
    else:
        # For other statuses, create inline spec
        from core.base.patterns.specification import spec as create_spec

        status_spec = create_spec(lambda p: p.status == status, f"status_{status.value}")

    return PedidoTenantSpec(tenant_id) & status_spec


def urgent_orders(min_items: int = 5) -> Specification[PedidoExample]:
    """Create composite spec for urgent orders needing immediate attention.

    Urgent orders are:
    - Still pending (not yet confirmed)
    - Have multiple items (min_items or more)
    - Need confirmation/review

    Example:
        >>> urgent = urgent_orders(min_items=10)
        >>> alerts = repository.find_all(urgent)
        >>> for order in alerts:
        ...     send_confirmation_reminder(order.customer_id)
    """
    return PedidoPendingSpec() & PedidoMinItemsSpec(min_items)


def customer_high_value_orders(
    customer_id: str, min_value: Decimal = Decimal("500.00")
) -> Specification[PedidoExample]:
    """Create composite spec for a customer's high-value orders (any status).

    Useful for:
    - Customer lifetime value analysis
    - Personalized marketing
    - Loyalty program qualification

    Example:
        >>> customer_premium = customer_high_value_orders(
        ...     "customer-456",
        ...     Decimal("1000.00")
        ... )
        >>> premium_orders = repository.find_all(customer_premium)
        >>> total_value = sum(order.total.amount for order in premium_orders)
        >>> if total_value > Decimal("10000.00"):
        ...     upgrade_to_vip_tier(customer_id)
    """
    return PedidoCustomerSpec(customer_id) & PedidoMinValueSpec(min_value)


def processable_bulk_orders(min_items: int = 15) -> Specification[PedidoExample]:
    """Create composite spec for bulk orders ready for processing.

    Combines bulk order detection with processing readiness.

    Example:
        >>> bulk_ready = processable_bulk_orders(min_items=20)
        >>> for order in repository.find_all(bulk_ready):
        ...     allocate_warehouse_space(order)
        ...     assign_multiple_pickers(order)
    """
    return orders_ready_for_processing() & bulk_orders(min_items)
