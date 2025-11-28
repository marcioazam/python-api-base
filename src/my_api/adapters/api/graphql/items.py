"""GraphQL types and resolvers for Item entity.

This module provides GraphQL integration for the Item entity,
demonstrating how to use the generic GraphQL types.

**Feature: api-architecture-analysis, Task 3.1: GraphQL Support with Strawberry**
**Validates: Requirements 4.5**
"""

from datetime import datetime

import strawberry

from my_api.adapters.api.graphql.types import (
    Connection,
    ConnectionArgs,
    Edge,
    PageInfo,
    connection_from_list,
)
from my_api.domain.entities.item import Item, ItemCreate, ItemResponse


@strawberry.type
class ItemType:
    """GraphQL type for Item entity."""

    id: str = strawberry.field(description="ULID identifier")
    name: str = strawberry.field(description="Item name")
    description: str | None = strawberry.field(description="Item description")
    price: float = strawberry.field(description="Item price")
    tax: float | None = strawberry.field(description="Tax amount")
    created_at: datetime = strawberry.field(description="Creation timestamp")
    updated_at: datetime = strawberry.field(description="Last update timestamp")

    @strawberry.field(description="Price including tax")
    def price_with_tax(self) -> float:
        """Calculate price including tax."""
        return self.price + (self.tax or 0)

    @classmethod
    def from_entity(cls, entity: Item | ItemResponse) -> "ItemType":
        """Create ItemType from Item entity or response DTO.

        Args:
            entity: The Item entity or ItemResponse DTO.

        Returns:
            ItemType instance.
        """
        return cls(
            id=entity.id,
            name=entity.name,
            description=entity.description,
            price=entity.price,
            tax=entity.tax,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )


@strawberry.type
class ItemEdge(Edge[ItemType]):
    """Edge type for Item connections."""

    pass


@strawberry.type
class ItemConnection(Connection[ItemType]):
    """Connection type for paginated Item queries."""

    pass


@strawberry.input
class ItemCreateInput:
    """Input type for creating items."""

    name: str = strawberry.field(description="Item name")
    description: str | None = strawberry.field(
        default=None, description="Item description"
    )
    price: float = strawberry.field(description="Item price (must be positive)")
    tax: float | None = strawberry.field(default=None, description="Tax amount")

    def to_dto(self) -> ItemCreate:
        """Convert to ItemCreate DTO."""
        return ItemCreate(
            name=self.name,
            description=self.description,
            price=self.price,
            tax=self.tax,
        )


@strawberry.input
class ItemUpdateInput:
    """Input type for updating items."""

    name: str | None = strawberry.field(default=None, description="Item name")
    description: str | None = strawberry.field(
        default=None, description="Item description"
    )
    price: float | None = strawberry.field(default=None, description="Item price")
    tax: float | None = strawberry.field(default=None, description="Tax amount")


def create_item_connection(
    items: list[ItemType],
    total_count: int,
    args: ConnectionArgs | None = None,
) -> ItemConnection:
    """Create an ItemConnection from a list of items.

    Args:
        items: List of ItemType instances.
        total_count: Total count of items.
        args: Pagination arguments.

    Returns:
        ItemConnection with proper pagination.
    """
    connection = connection_from_list(
        items=items,
        args=args,
        total_count=total_count,
        cursor_prefix="item",
    )

    return ItemConnection(
        edges=[
            ItemEdge(node=edge.node, cursor=edge.cursor)
            for edge in connection.edges
        ],
        page_info=PageInfo(
            has_previous_page=connection.page_info.has_previous_page,
            has_next_page=connection.page_info.has_next_page,
            start_cursor=connection.page_info.start_cursor,
            end_cursor=connection.page_info.end_cursor,
        ),
        total_count=connection.total_count,
    )
