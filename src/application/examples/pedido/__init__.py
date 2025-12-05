"""Application layer for PedidoExample.

Organized into subpackages by responsibility:
- commands/: Pedido commands
- queries/: Pedido queries
- handlers/: Command/Query handlers
- use_cases/: Business logic
- dtos/: Data transfer objects
- mappers/: Entity ↔ DTO mapping

**Feature: application-common-integration**
"""

from application.examples.pedido.commands import (
    CreatePedidoCommand,
    DeletePedidoCommand,
    UpdatePedidoCommand,
)
from application.examples.pedido.dtos import (
    PedidoCreate,
    PedidoResponse,
    PedidoUpdate,
)
from application.examples.pedido.handlers import (
    CreatePedidoHandler,
    DeletePedidoHandler,
    GetPedidoByIdHandler,
    ListPedidosHandler,
    UpdatePedidoHandler,
)
from application.examples.pedido.mappers import PedidoMapper
from application.examples.pedido.queries import (
    GetPedidoByIdQuery,
    ListPedidosQuery,
)
from application.examples.pedido.use_cases import PedidoUseCase

__all__ = [
    # Commands
    "CreatePedidoCommand",
    "UpdatePedidoCommand",
    "DeletePedidoCommand",
    # Queries
    "GetPedidoByIdQuery",
    "ListPedidosQuery",
    # Handlers
    "CreatePedidoHandler",
    "UpdatePedidoHandler",
    "DeletePedidoHandler",
    "GetPedidoByIdHandler",
    "ListPedidosHandler",
    # DTOs
    "PedidoCreate",
    "PedidoUpdate",
    "PedidoResponse",
    # Mapper
    "PedidoMapper",
    # Use Case
    "PedidoUseCase",
]
