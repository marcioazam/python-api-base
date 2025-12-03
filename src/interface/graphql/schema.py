"""GraphQL Schema for Examples using Strawberry.

Provides GraphQL queries and mutations for ItemExample and PedidoExample.

**Feature: interface-modules-workflow-analysis**
**Validates: Requirements 3.1, 3.2, 3.3**
"""

from datetime import datetime
from typing import Any
from collections.abc import AsyncIterator

import strawberry
from strawberry.types import Info

from interface.graphql.dataloader import DataLoader, DataLoaderConfig


@strawberry.type
class ItemExampleType:
    """GraphQL type for ItemExample."""

    id: str
    name: str
    description: str | None
    category: str
    price: float
    quantity: int
    status: str
    created_at: datetime
    updated_at: datetime | None


@strawberry.type
class PedidoItemType:
    """GraphQL type for items in a Pedido."""

    item_id: str
    quantity: int
    unit_price: float


@strawberry.type
class PedidoExampleType:
    """GraphQL type for PedidoExample."""

    id: str
    customer_id: str
    status: str
    items: list[PedidoItemType]
    total: float
    created_at: datetime
    confirmed_at: datetime | None
    cancelled_at: datetime | None


@strawberry.type
class PageInfoType:
    """Relay-style pagination info."""

    has_next_page: bool
    has_previous_page: bool
    start_cursor: str | None
    end_cursor: str | None


@strawberry.type
class ItemEdge:
    """Edge type for Item connection."""

    node: ItemExampleType
    cursor: str


@strawberry.type
class ItemConnection:
    """Relay-style connection for Items."""

    edges: list[ItemEdge]
    page_info: PageInfoType
    total_count: int


@strawberry.type
class PedidoEdge:
    """Edge type for Pedido connection."""

    node: PedidoExampleType
    cursor: str


@strawberry.type
class PedidoConnection:
    """Relay-style connection for Pedidos."""

    edges: list[PedidoEdge]
    page_info: PageInfoType
    total_count: int


@strawberry.input
class ItemCreateInput:
    """Input for creating an Item."""

    name: str
    description: str | None = None
    category: str
    price: float
    quantity: int = 0


@strawberry.input
class ItemUpdateInput:
    """Input for updating an Item."""

    name: str | None = None
    description: str | None = None
    category: str | None = None
    price: float | None = None
    quantity: int | None = None


@strawberry.input
class PedidoCreateInput:
    """Input for creating a Pedido."""

    customer_id: str


@strawberry.input
class AddItemToPedidoInput:
    """Input for adding item to Pedido."""

    item_id: str
    quantity: int


@strawberry.type
class MutationResult:
    """Generic mutation result."""

    success: bool
    message: str | None = None


@strawberry.type
class ItemMutationResult:
    """Result of Item mutation."""

    success: bool
    item: ItemExampleType | None = None
    error: str | None = None


@strawberry.type
class PedidoMutationResult:
    """Result of Pedido mutation."""

    success: bool
    pedido: PedidoExampleType | None = None
    error: str | None = None


def get_item_repository(info: Info) -> Any:
    """Get ItemExampleRepository from context."""
    return info.context.get("item_repository")


def get_pedido_repository(info: Info) -> Any:
    """Get PedidoExampleRepository from context."""
    return info.context.get("pedido_repository")


@strawberry.type
class Query:
    """GraphQL Query root for Examples."""

    @strawberry.field
    async def item(self, info: Info, id: str) -> ItemExampleType | None:
        """Get a single item by ID.

        **Feature: interface-modules-workflow-analysis**
        **Validates: Requirements 3.1**
        """
        repo = get_item_repository(info)
        if repo is None:
            return None
        result = await repo.get_by_id(id)
        if result is None:
            return None
        return ItemExampleType(
            id=str(result.id),
            name=result.name,
            description=result.description,
            category=result.category,
            price=float(result.price),
            quantity=result.quantity,
            status=result.status,
            created_at=result.created_at,
            updated_at=result.updated_at,
        )

    @strawberry.field
    async def items(
        self,
        info: Info,
        first: int = 10,
        after: str | None = None,
        category: str | None = None,
    ) -> ItemConnection:
        """Get paginated list of items with Relay-style connection.

        **Feature: interface-modules-workflow-analysis**
        **Validates: Requirements 3.2**
        """
        repo = get_item_repository(info)
        if repo is None:
            return ItemConnection(
                edges=[],
                page_info=PageInfoType(
                    has_next_page=False,
                    has_previous_page=False,
                    start_cursor=None,
                    end_cursor=None,
                ),
                total_count=0,
            )

        offset = 0
        if after:
            try:
                offset = int(after) + 1
            except ValueError:
                offset = 0

        items = await repo.list_all(limit=first + 1, offset=offset)
        has_next = len(items) > first
        items = items[:first]

        edges = [
            ItemEdge(
                node=ItemExampleType(
                    id=str(item.id),
                    name=item.name,
                    description=item.description,
                    category=item.category,
                    price=float(item.price),
                    quantity=item.quantity,
                    status=item.status,
                    created_at=item.created_at,
                    updated_at=item.updated_at,
                ),
                cursor=str(offset + i),
            )
            for i, item in enumerate(items)
        ]

        return ItemConnection(
            edges=edges,
            page_info=PageInfoType(
                has_next_page=has_next,
                has_previous_page=offset > 0,
                start_cursor=edges[0].cursor if edges else None,
                end_cursor=edges[-1].cursor if edges else None,
            ),
            total_count=len(edges),
        )

    @strawberry.field
    async def pedido(self, info: Info, id: str) -> PedidoExampleType | None:
        """Get a single pedido by ID.

        **Feature: interface-modules-workflow-analysis**
        **Validates: Requirements 3.1**
        """
        repo = get_pedido_repository(info)
        if repo is None:
            return None
        result = await repo.get_by_id(id)
        if result is None:
            return None
        return PedidoExampleType(
            id=str(result.id),
            customer_id=result.customer_id,
            status=result.status,
            items=[
                PedidoItemType(
                    item_id=str(item.get("item_id", "")),
                    quantity=item.get("quantity", 0),
                    unit_price=float(item.get("unit_price", 0)),
                )
                for item in (result.items or [])
            ],
            total=float(result.total or 0),
            created_at=result.created_at,
            confirmed_at=result.confirmed_at,
            cancelled_at=result.cancelled_at,
        )

    @strawberry.field
    async def pedidos(
        self,
        info: Info,
        first: int = 10,
        after: str | None = None,
        customer_id: str | None = None,
    ) -> PedidoConnection:
        """Get paginated list of pedidos with Relay-style connection.

        **Feature: interface-modules-workflow-analysis**
        **Validates: Requirements 3.2**
        """
        repo = get_pedido_repository(info)
        if repo is None:
            return PedidoConnection(
                edges=[],
                page_info=PageInfoType(
                    has_next_page=False,
                    has_previous_page=False,
                    start_cursor=None,
                    end_cursor=None,
                ),
                total_count=0,
            )

        offset = 0
        if after:
            try:
                offset = int(after) + 1
            except ValueError:
                offset = 0

        pedidos = await repo.list_all(limit=first + 1, offset=offset)
        has_next = len(pedidos) > first
        pedidos = pedidos[:first]

        edges = [
            PedidoEdge(
                node=PedidoExampleType(
                    id=str(p.id),
                    customer_id=p.customer_id,
                    status=p.status,
                    items=[
                        PedidoItemType(
                            item_id=str(item.get("item_id", "")),
                            quantity=item.get("quantity", 0),
                            unit_price=float(item.get("unit_price", 0)),
                        )
                        for item in (p.items or [])
                    ],
                    total=float(p.total or 0),
                    created_at=p.created_at,
                    confirmed_at=p.confirmed_at,
                    cancelled_at=p.cancelled_at,
                ),
                cursor=str(offset + i),
            )
            for i, p in enumerate(pedidos)
        ]

        return PedidoConnection(
            edges=edges,
            page_info=PageInfoType(
                has_next_page=has_next,
                has_previous_page=offset > 0,
                start_cursor=edges[0].cursor if edges else None,
                end_cursor=edges[-1].cursor if edges else None,
            ),
            total_count=len(edges),
        )


@strawberry.type
class Mutation:
    """GraphQL Mutation root for Examples."""

    @strawberry.mutation
    async def create_item(
        self, info: Info, input: ItemCreateInput
    ) -> ItemMutationResult:
        """Create a new item.

        **Feature: interface-modules-workflow-analysis**
        **Validates: Requirements 3.3**
        """
        repo = get_item_repository(info)
        if repo is None:
            return ItemMutationResult(
                success=False, error="Repository not available"
            )

        try:
            from application.examples import ItemExampleCreate

            create_dto = ItemExampleCreate(
                name=input.name,
                description=input.description,
                category=input.category,
                price=input.price,
                quantity=input.quantity,
            )
            result = await repo.create(create_dto)
            return ItemMutationResult(
                success=True,
                item=ItemExampleType(
                    id=str(result.id),
                    name=result.name,
                    description=result.description,
                    category=result.category,
                    price=float(result.price),
                    quantity=result.quantity,
                    status=result.status,
                    created_at=result.created_at,
                    updated_at=result.updated_at,
                ),
            )
        except Exception as e:
            return ItemMutationResult(success=False, error=str(e))

    @strawberry.mutation
    async def update_item(
        self, info: Info, id: str, input: ItemUpdateInput
    ) -> ItemMutationResult:
        """Update an existing item.

        **Feature: interface-modules-workflow-analysis**
        **Validates: Requirements 3.3**
        """
        repo = get_item_repository(info)
        if repo is None:
            return ItemMutationResult(
                success=False, error="Repository not available"
            )

        try:
            existing = await repo.get_by_id(id)
            if existing is None:
                return ItemMutationResult(success=False, error="Item not found")

            update_data = {}
            if input.name is not None:
                update_data["name"] = input.name
            if input.description is not None:
                update_data["description"] = input.description
            if input.category is not None:
                update_data["category"] = input.category
            if input.price is not None:
                update_data["price"] = input.price
            if input.quantity is not None:
                update_data["quantity"] = input.quantity

            result = await repo.update(id, update_data)
            return ItemMutationResult(
                success=True,
                item=ItemExampleType(
                    id=str(result.id),
                    name=result.name,
                    description=result.description,
                    category=result.category,
                    price=float(result.price),
                    quantity=result.quantity,
                    status=result.status,
                    created_at=result.created_at,
                    updated_at=result.updated_at,
                ),
            )
        except Exception as e:
            return ItemMutationResult(success=False, error=str(e))

    @strawberry.mutation
    async def delete_item(self, info: Info, id: str) -> MutationResult:
        """Delete an item.

        **Feature: interface-modules-workflow-analysis**
        **Validates: Requirements 3.3**
        """
        repo = get_item_repository(info)
        if repo is None:
            return MutationResult(success=False, message="Repository not available")

        try:
            await repo.delete(id)
            return MutationResult(success=True, message="Item deleted")
        except Exception as e:
            return MutationResult(success=False, message=str(e))

    @strawberry.mutation
    async def create_pedido(
        self, info: Info, input: PedidoCreateInput
    ) -> PedidoMutationResult:
        """Create a new pedido.

        **Feature: interface-modules-workflow-analysis**
        **Validates: Requirements 3.3**
        """
        repo = get_pedido_repository(info)
        if repo is None:
            return PedidoMutationResult(
                success=False, error="Repository not available"
            )

        try:
            from application.examples import PedidoExampleCreate

            create_dto = PedidoExampleCreate(customer_id=input.customer_id)
            result = await repo.create(create_dto)
            return PedidoMutationResult(
                success=True,
                pedido=PedidoExampleType(
                    id=str(result.id),
                    customer_id=result.customer_id,
                    status=result.status,
                    items=[],
                    total=0.0,
                    created_at=result.created_at,
                    confirmed_at=None,
                    cancelled_at=None,
                ),
            )
        except Exception as e:
            return PedidoMutationResult(success=False, error=str(e))

    @strawberry.mutation
    async def confirm_pedido(self, info: Info, id: str) -> PedidoMutationResult:
        """Confirm a pedido.

        **Feature: interface-modules-workflow-analysis**
        **Validates: Requirements 3.3**
        """
        repo = get_pedido_repository(info)
        if repo is None:
            return PedidoMutationResult(
                success=False, error="Repository not available"
            )

        try:
            result = await repo.update(id, {"status": "confirmed"})
            return PedidoMutationResult(
                success=True,
                pedido=PedidoExampleType(
                    id=str(result.id),
                    customer_id=result.customer_id,
                    status=result.status,
                    items=[
                        PedidoItemType(
                            item_id=str(item.get("item_id", "")),
                            quantity=item.get("quantity", 0),
                            unit_price=float(item.get("unit_price", 0)),
                        )
                        for item in (result.items or [])
                    ],
                    total=float(result.total or 0),
                    created_at=result.created_at,
                    confirmed_at=result.confirmed_at,
                    cancelled_at=result.cancelled_at,
                ),
            )
        except Exception as e:
            return PedidoMutationResult(success=False, error=str(e))


schema = strawberry.Schema(query=Query, mutation=Mutation)
