"""Application layer for Example system.

Contains DTOs, mappers, use cases for ItemExample and PedidoExample.
Organized by bounded context following DDD principles.

**Feature: example-system-demo**
"""

# Shared
from application.examples.shared import (
    MoneyDTO,
    UseCaseError,
    NotFoundError,
    ValidationError,
)

# Item bounded context
from application.examples.item import (
    ItemExampleCreate,
    ItemExampleUpdate,
    ItemExampleResponse,
    ItemExampleListResponse,
    ItemExampleMapper,
    ItemExampleUseCase,
)

# Pedido bounded context
from application.examples.pedido import (
    PedidoExampleCreate,
    PedidoExampleUpdate,
    PedidoExampleResponse,
    PedidoItemResponse,
    AddItemRequest,
    ConfirmPedidoRequest,
    CancelPedidoRequest,
    UpdateStatusRequest,
    PedidoExampleMapper,
    PedidoItemMapper,
    PedidoExampleUseCase,
)

__all__ = [
    # Shared
    "MoneyDTO",
    "UseCaseError",
    "NotFoundError",
    "ValidationError",
    # Item
    "ItemExampleCreate",
    "ItemExampleUpdate",
    "ItemExampleResponse",
    "ItemExampleListResponse",
    "ItemExampleMapper",
    "ItemExampleUseCase",
    # Pedido
    "PedidoExampleCreate",
    "PedidoExampleUpdate",
    "PedidoExampleResponse",
    "PedidoItemResponse",
    "AddItemRequest",
    "ConfirmPedidoRequest",
    "CancelPedidoRequest",
    "UpdateStatusRequest",
    "PedidoExampleMapper",
    "PedidoItemMapper",
    "PedidoExampleUseCase",
]
