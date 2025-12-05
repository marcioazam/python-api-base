"""Pedido example handlers (Command/Query handlers).

**Feature: example-system-demo**
"""

from application.examples.pedido.handlers.handlers import (
    CreatePedidoHandler,
    DeletePedidoHandler,
    GetPedidoByIdHandler,
    ListPedidosHandler,
    UpdatePedidoHandler,
)

__all__ = [
    "CreatePedidoHandler",
    "UpdatePedidoHandler",
    "DeletePedidoHandler",
    "GetPedidoByIdHandler",
    "ListPedidosHandler",
]
