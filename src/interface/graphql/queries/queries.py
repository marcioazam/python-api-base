"""GraphQL Query root for Examples.

**Feature: interface-modules-workflow-analysis**
**Validates: Requirements 3.1, 3.2**
**Improvement: P2-1 - Use CQRS pattern**
"""

import strawberry
from strawberry.types import Info

from application.common.cqrs import QueryBus
from application.examples.item.queries import GetItemQuery, ListItemsQuery
from application.examples.pedido.queries import GetPedidoQuery, ListPedidosQuery
from core.base.patterns.result import Err, Ok
from application.mappers.graphql import (
    create_empty_item_connection,
    create_empty_pedido_connection,
    create_item_connection,
    create_pedido_connection,
    map_item_dto_to_type,
    map_pedido_dto_to_type,
    parse_cursor_to_page,
)
from interface.graphql.types import (
    ItemConnection,
    ItemExampleType,
    PedidoConnection,
    PedidoExampleType,
)


def get_query_bus(info: Info) -> QueryBus | None:
    """Get QueryBus from context."""
    return info.context.get("query_bus")


@strawberry.type
class Query:
    """GraphQL Query root for Examples."""

    @strawberry.field
    async def item(self, info: Info, id: str) -> ItemExampleType | None:
        """Get a single item by ID."""
        query_bus = get_query_bus(info)
        if query_bus is None:
            return None

        query = GetItemQuery(item_id=id)
        result = await query_bus.dispatch(query)

        match result:
            case Ok(item_dto):
                return map_item_dto_to_type(item_dto)
            case Err(_):
                return None

    @strawberry.field
    async def items(
        self,
        info: Info,
        first: int = 10,
        after: str | None = None,
        category: str | None = None,
    ) -> ItemConnection:
        """Get paginated list of items with Relay-style connection."""
        query_bus = get_query_bus(info)
        if query_bus is None:
            return create_empty_item_connection()

        page = parse_cursor_to_page(after, first)
        query = ListItemsQuery(page=page, size=first, category=category)
        result = await query_bus.dispatch(query)

        match result:
            case Ok(paginated_response):
                return create_item_connection(
                    items=paginated_response.items,
                    page=page,
                    page_size=first,
                    total=paginated_response.total,
                )
            case Err(_):
                return create_empty_item_connection()

    @strawberry.field
    async def pedido(self, info: Info, id: str) -> PedidoExampleType | None:
        """Get a single pedido by ID."""
        query_bus = get_query_bus(info)
        if query_bus is None:
            return None

        query = GetPedidoQuery(pedido_id=id)
        result = await query_bus.dispatch(query)

        match result:
            case Ok(pedido_dto):
                return map_pedido_dto_to_type(pedido_dto)
            case Err(_):
                return None

    @strawberry.field
    async def pedidos(
        self,
        info: Info,
        first: int = 10,
        after: str | None = None,
        customer_id: str | None = None,
    ) -> PedidoConnection:
        """Get paginated list of pedidos with Relay-style connection."""
        query_bus = get_query_bus(info)
        if query_bus is None:
            return create_empty_pedido_connection()

        page = parse_cursor_to_page(after, first)
        query = ListPedidosQuery(page=page, size=first, customer_id=customer_id)
        result = await query_bus.dispatch(query)

        match result:
            case Ok(paginated_response):
                return create_pedido_connection(
                    pedidos=paginated_response.items,
                    page=page,
                    page_size=first,
                    total=paginated_response.total,
                )
            case Err(_):
                return create_empty_pedido_connection()
