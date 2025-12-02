"""Application layer for Example system.

Contains DTOs, mappers, use cases, and CQRS handlers
for ItemExample and PedidoExample.

**Feature: example-system-demo**
"""

from application.examples.dtos import (
    # Item DTOs
    ItemExampleCreate,
    ItemExampleUpdate,
    ItemExampleResponse,
    ItemExampleListResponse,
    # Pedido DTOs
    PedidoExampleCreate,
    PedidoExampleUpdate,
    PedidoExampleResponse,
    PedidoItemResponse,
    AddItemRequest,
)
from application.examples.use_cases import (
    ItemExampleUseCase,
    PedidoExampleUseCase,
)

__all__ = [
    # Item DTOs
    "ItemExampleCreate",
    "ItemExampleUpdate",
    "ItemExampleResponse",
    "ItemExampleListResponse",
    # Pedido DTOs
    "PedidoExampleCreate",
    "PedidoExampleUpdate",
    "PedidoExampleResponse",
    "PedidoItemResponse",
    "AddItemRequest",
    # Use Cases
    "ItemExampleUseCase",
    "PedidoExampleUseCase",
]
