"""Application layer for Example system.

Contains DTOs, mappers, use cases for ItemExample and PedidoExample.
Organized by bounded context following DDD principles.

Structure:
- item/: Item example with commands, queries, handlers, use cases, batch, export
- pedido/: Pedido example with commands, queries, handlers, use cases
- shared/: Shared DTOs and errors

**Feature: example-system-demo**
"""

# Item bounded context
from application.examples.item import (
    BatchCreateRequest,
    BatchUpdateRequest,
    CreateItemCommand,
    CreateItemHandler,
    DeleteItemCommand,
    DeleteItemHandler,
    ExportFormat,
    ExportMetadata,
    ExportResult,
    GetItemByIdHandler,
    GetItemByIdQuery,
    ImportResult,
    ItemExampleBatchService,
    ItemExampleCreate,
    ItemExampleExportService,
    ItemExampleImportService,
    ItemExampleMapper,
    ItemExampleResponse,
    ItemExampleUpdate,
    ItemExampleUseCase,
    ListItemsHandler,
    ListItemsQuery,
    UpdateItemCommand,
    UpdateItemHandler,
)

# Pedido bounded context
from application.examples.pedido import (
    CreatePedidoCommand,
    CreatePedidoHandler,
    DeletePedidoCommand,
    DeletePedidoHandler,
    GetPedidoByIdHandler,
    GetPedidoByIdQuery,
    ListPedidosHandler,
    ListPedidosQuery,
    PedidoCreate,
    PedidoMapper,
    PedidoResponse,
    PedidoUpdate,
    PedidoUseCase,
    UpdatePedidoCommand,
    UpdatePedidoHandler,
)

# Shared
from application.examples.shared import (
    MoneyDTO,
    NotFoundError,
    UseCaseError,
    ValidationError,
)

__all__ = [
    # Item Commands
    "CreateItemCommand",
    "UpdateItemCommand",
    "DeleteItemCommand",
    # Item Queries
    "GetItemByIdQuery",
    "ListItemsQuery",
    # Item Handlers
    "CreateItemHandler",
    "UpdateItemHandler",
    "DeleteItemHandler",
    "GetItemByIdHandler",
    "ListItemsHandler",
    # Item DTOs
    "ItemExampleCreate",
    "ItemExampleUpdate",
    "ItemExampleResponse",
    # Item Mapper
    "ItemExampleMapper",
    # Item Batch
    "BatchCreateRequest",
    "BatchUpdateRequest",
    "ItemExampleBatchService",
    # Item Export
    "ExportFormat",
    "ExportMetadata",
    "ExportResult",
    "ImportResult",
    "ItemExampleExportService",
    "ItemExampleImportService",
    # Item Use Case
    "ItemExampleUseCase",
    # Pedido Commands
    "CreatePedidoCommand",
    "UpdatePedidoCommand",
    "DeletePedidoCommand",
    # Pedido Queries
    "GetPedidoByIdQuery",
    "ListPedidosQuery",
    # Pedido Handlers
    "CreatePedidoHandler",
    "UpdatePedidoHandler",
    "DeletePedidoHandler",
    "GetPedidoByIdHandler",
    "ListPedidosHandler",
    # Pedido DTOs
    "PedidoCreate",
    "PedidoUpdate",
    "PedidoResponse",
    # Pedido Mapper
    "PedidoMapper",
    # Pedido Use Case
    "PedidoUseCase",
    # Shared DTOs
    "MoneyDTO",
    # Shared Errors
    "NotFoundError",
    "UseCaseError",
    "ValidationError",
]
