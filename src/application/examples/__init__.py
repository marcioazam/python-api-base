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
from application.examples.errors import (
    UseCaseError,
    NotFoundError,
    ValidationError,
)
from application.examples.item_use_case import ItemExampleUseCase
from application.examples.pedido_use_case import PedidoExampleUseCase

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
    # Errors
    "UseCaseError",
    "NotFoundError",
    "ValidationError",
    # Use Cases
    "ItemExampleUseCase",
    "PedidoExampleUseCase",
]
