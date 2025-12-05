"""CQRS Queries for PedidoExample.

**Feature: application-common-integration**
**Validates: Requirements 3.5, 3.6**
"""

from dataclasses import dataclass

from application.common.dto import PaginatedResponse
from application.examples.pedido.dtos import PedidoExampleResponse
from core.base.cqrs.query import BaseQuery


@dataclass(frozen=True, kw_only=True)
class GetPedidoQuery(BaseQuery[PedidoExampleResponse]):
    """Query to get a single PedidoExample by ID."""

    pedido_id: str


@dataclass(frozen=True, kw_only=True)
class ListPedidosQuery(BaseQuery[PaginatedResponse[PedidoExampleResponse]]):
    """Query to list PedidoExamples with pagination and filters."""

    page: int = 1
    size: int = 20
    customer_id: str | None = None
    status: str | None = None
    tenant_id: str | None = None
    sort_by: str = "created_at"
    sort_order: str = "desc"
