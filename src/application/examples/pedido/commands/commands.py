"""CQRS Commands for PedidoExample.

**Feature: application-common-integration**
**Validates: Requirements 3.1, 3.2, 3.3, 3.4**
"""

from dataclasses import dataclass, field
from decimal import Decimal

from core.base.cqrs.command import BaseCommand


@dataclass(frozen=True, kw_only=True)
class CreatePedidoCommand(BaseCommand):
    """Command to create a new PedidoExample."""

    customer_id: str
    customer_name: str
    customer_email: str
    shipping_address: str = ""
    notes: str = ""
    items: list[dict] = field(default_factory=list)
    tenant_id: str | None = None
    created_by: str = "system"


@dataclass(frozen=True, kw_only=True)
class AddItemToPedidoCommand(BaseCommand):
    """Command to add an item to an existing PedidoExample."""

    pedido_id: str
    item_id: str
    quantity: int = 1
    discount: Decimal = field(default_factory=lambda: Decimal("0"))


@dataclass(frozen=True, kw_only=True)
class ConfirmPedidoCommand(BaseCommand):
    """Command to confirm a PedidoExample."""

    pedido_id: str
    confirmed_by: str = "system"


@dataclass(frozen=True, kw_only=True)
class CancelPedidoCommand(BaseCommand):
    """Command to cancel a PedidoExample."""

    pedido_id: str
    reason: str
    cancelled_by: str = "system"
