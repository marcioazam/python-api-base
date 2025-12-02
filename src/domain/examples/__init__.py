"""Example domain module demonstrating all system features.

This module contains ItemExample and PedidoExample aggregates
to showcase the complete Python API Base 2025 architecture.

**Feature: example-system-demo**
**Purpose: Development reference and testing**

To disable for production, see: docs/example-system-deactivation.md
"""

from domain.examples.item_example import (
    ItemExample,
    ItemExampleStatus,
    Money,
    ItemExampleCreated,
    ItemExampleUpdated,
    ItemExampleDeleted,
)
from domain.examples.pedido_example import (
    PedidoExample,
    PedidoItemExample,
    PedidoStatus,
    PedidoCreated,
    PedidoItemAdded,
    PedidoCompleted,
)
from domain.examples.specifications import (
    ItemExampleActiveSpec,
    ItemExamplePriceRangeSpec,
    PedidoPendingSpec,
    PedidoMinValueSpec,
)

__all__ = [
    # Item
    "ItemExample",
    "ItemExampleStatus",
    "Money",
    "ItemExampleCreated",
    "ItemExampleUpdated",
    "ItemExampleDeleted",
    # Pedido
    "PedidoExample",
    "PedidoItemExample",
    "PedidoStatus",
    "PedidoCreated",
    "PedidoItemAdded",
    "PedidoCompleted",
    # Specifications
    "ItemExampleActiveSpec",
    "ItemExamplePriceRangeSpec",
    "PedidoPendingSpec",
    "PedidoMinValueSpec",
]
