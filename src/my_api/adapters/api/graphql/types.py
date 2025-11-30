"""Generic GraphQL types for Relay-style pagination.

This module provides generic Edge, Connection, and PageInfo types
following the Relay Connection specification for cursor-based pagination.

**Feature: api-architecture-analysis, Task 3.1: GraphQL Support with Strawberry**
**Validates: Requirements 4.5**

Usage:
    from my_api.adapters.api.graphql.types import Edge, Connection, PageInfo

    @strawberry.type
    class ItemEdge(Edge[ItemType]):
        pass

    @strawberry.type
    class ItemConnection(Connection[ItemType]):
        pass
"""

from collections.abc import Sequence
from dataclasses import dataclass

import strawberry


@strawberry.type
class PageInfo:
    """Pagination information for Relay-style connections.

    Provides cursor-based pagination metadata following the
    Relay Connection specification.
    """

    has_previous_page: bool = strawberry.field(
        description="Whether there are more items before the current page"
    )
    has_next_page: bool = strawberry.field(
        description="Whether there are more items after the current page"
    )
    start_cursor: str | None = strawberry.field(
        default=None,
        description="Cursor of the first item in the current page",
    )
    end_cursor: str | None = strawberry.field(
        default=None,
        description="Cursor of the last item in the current page",
    )


@strawberry.type
class Edge[T]:
    """Generic edge type for Relay-style connections.

    An edge represents a single item in a connection along with
    its cursor for pagination.

    Type Parameters:
        T: The node type contained in this edge.
    """

    node: T = strawberry.field(description="The item at the end of the edge")
    cursor: str = strawberry.field(
        description="Opaque cursor for pagination"
    )


@strawberry.type
class Connection[T]:
    """Generic connection type for Relay-style pagination.

    A connection represents a paginated list of items with
    edges and pagination information.

    Type Parameters:
        T: The node type contained in this connection's edges.
    """

    edges: list[Edge[T]] = strawberry.field(
        description="List of edges containing nodes"
    )
    page_info: PageInfo = strawberry.field(
        description="Pagination information"
    )
    total_count: int = strawberry.field(
        description="Total number of items in the connection"
    )


@dataclass
class ConnectionArgs:
    """Arguments for connection-based pagination.

    Supports both forward and backward pagination following
    the Relay Connection specification.
    """

    first: int | None = None
    after: str | None = None
    last: int | None = None
    before: str | None = None


def encode_cursor(value: str | int, prefix: str = "cursor") -> str:
    """Encode a value as an opaque cursor string.

    Creates a base64-encoded cursor that can be used for pagination.
    The cursor format is "{prefix}:{value}" encoded in base64.

    Args:
        value: The value to encode (typically an ID or offset).
        prefix: Optional prefix for the cursor (default: "cursor").

    Returns:
        Base64-encoded cursor string.

    Raises:
        TypeError: If value cannot be converted to string.

    Example:
        >>> encode_cursor(5)
        'Y3Vyc29yOjU='
        >>> encode_cursor("abc", prefix="item")
        'aXRlbTphYmM='
    """
    import base64

    cursor_str = f"{prefix}:{value}"
    return base64.b64encode(cursor_str.encode()).decode()


def decode_cursor(cursor: str, prefix: str = "cursor") -> str:
    """Decode an opaque cursor string with safe error handling.

    Args:
        cursor: The cursor string to decode.
        prefix: Expected prefix for validation.

    Returns:
        The decoded value.

    Raises:
        ValueError: If the cursor is invalid (generic message, no internal details).
    """
    import base64

    # Handle empty cursor input
    if not cursor or not cursor.strip():
        raise ValueError("Invalid cursor")

    try:
        decoded = base64.b64decode(cursor.encode()).decode()
        parts = decoded.split(":", 1)
        if len(parts) != 2 or parts[0] != prefix:
            raise ValueError("Invalid cursor")
        return parts[1]
    except ValueError:
        # Re-raise ValueError as-is (already has generic message)
        raise
    except Exception:
        # Catch all other exceptions and raise generic error
        # Do not expose internal details like base64 decode errors
        raise ValueError("Invalid cursor")


def connection_from_list(
    items: Sequence[T],
    args: ConnectionArgs | None = None,
    total_count: int | None = None,
    cursor_prefix: str = "cursor",
) -> Connection[T]:
    """Create a Connection from a list of items.

    Implements cursor-based pagination following the Relay
    Connection specification.

    Args:
        items: The list of items to paginate.
        args: Pagination arguments (first, after, last, before).
        total_count: Total count of items (defaults to len(items)).
        cursor_prefix: Prefix for cursor encoding.

    Returns:
        A Connection containing the paginated items.

    Example:
        items = [item1, item2, item3, item4, item5]
        args = ConnectionArgs(first=2, after=encode_cursor(1))
        connection = connection_from_list(items, args)
        # Returns items 2 and 3 with proper pagination info
    """
    if args is None:
        args = ConnectionArgs()

    total = total_count if total_count is not None else len(items)
    items_list = list(items)

    # Apply cursor-based slicing
    start_index = 0
    end_index = len(items_list)

    if args.after:
        try:
            after_index = int(decode_cursor(args.after, cursor_prefix))
            start_index = after_index + 1
        except (ValueError, TypeError):
            pass

    if args.before:
        try:
            before_index = int(decode_cursor(args.before, cursor_prefix))
            end_index = before_index
        except (ValueError, TypeError):
            pass

    # Apply first/last limits
    sliced_items = items_list[start_index:end_index]

    if args.first is not None:
        sliced_items = sliced_items[: args.first]
    elif args.last is not None:
        sliced_items = sliced_items[-args.last :]

    # Create edges with cursors
    edges: list[Edge[T]] = []
    for i, item in enumerate(sliced_items):
        actual_index = start_index + i
        cursor = encode_cursor(actual_index, cursor_prefix)
        edges.append(Edge(node=item, cursor=cursor))

    # Calculate page info
    has_previous = start_index > 0
    has_next = (start_index + len(sliced_items)) < len(items_list)

    start_cursor = edges[0].cursor if edges else None
    end_cursor = edges[-1].cursor if edges else None

    page_info = PageInfo(
        has_previous_page=has_previous,
        has_next_page=has_next,
        start_cursor=start_cursor,
        end_cursor=end_cursor,
    )

    return Connection(
        edges=edges,
        page_info=page_info,
        total_count=total,
    )
