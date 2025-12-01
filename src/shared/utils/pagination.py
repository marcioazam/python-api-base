"""Generic pagination utilities with offset and cursor-based pagination."""

import base64
from dataclasses import dataclass
from collections.abc import Sequence


@dataclass(frozen=True, slots=True)
class OffsetPaginationParams:
    """Parameters for offset-based pagination."""

    page: int = 1
    size: int = 20

    def __post_init__(self) -> None:
        """Validate pagination parameters."""
        if self.page < 1:
            object.__setattr__(self, "page", 1)
        if self.size < 1:
            object.__setattr__(self, "size", 1)
        if self.size > 100:
            object.__setattr__(self, "size", 100)

    @property
    def skip(self) -> int:
        """Calculate number of items to skip."""
        return (self.page - 1) * self.size

    @property
    def limit(self) -> int:
        """Get limit (same as size)."""
        return self.size


@dataclass(frozen=True, slots=True)
class OffsetPaginationResult[T]:
    """Result of offset-based pagination."""

    items: Sequence[T]
    total: int
    page: int
    size: int

    @property
    def pages(self) -> int:
        """Calculate total number of pages."""
        if self.total == 0:
            return 0
        return (self.total + self.size - 1) // self.size

    @property
    def has_next(self) -> bool:
        """Check if there is a next page."""
        return self.page < self.pages

    @property
    def has_previous(self) -> bool:
        """Check if there is a previous page."""
        return self.page > 1


def paginate_offset[T](
    items: Sequence[T],
    total: int,
    params: OffsetPaginationParams,
) -> OffsetPaginationResult[T]:
    """Create pagination result from items.

    Args:
        items: Items for current page.
        total: Total count of all items.
        params: Pagination parameters.

    Returns:
        OffsetPaginationResult: Paginated result.
    """
    return OffsetPaginationResult(
        items=items,
        total=total,
        page=params.page,
        size=params.size,
    )


def paginate_list[T](
    items: Sequence[T],
    params: OffsetPaginationParams,
) -> OffsetPaginationResult[T]:
    """Paginate an in-memory list.

    Args:
        items: Full list of items.
        params: Pagination parameters.

    Returns:
        OffsetPaginationResult: Paginated result.
    """
    total = len(items)
    start = params.skip
    end = start + params.size
    page_items = items[start:end]

    return OffsetPaginationResult(
        items=page_items,
        total=total,
        page=params.page,
        size=params.size,
    )


# Cursor-based pagination


def encode_cursor(value: str) -> str:
    """Encode a cursor value to base64.

    Args:
        value: Value to encode.

    Returns:
        str: Base64 encoded cursor.
    """
    return base64.urlsafe_b64encode(value.encode()).decode()


def decode_cursor(cursor: str) -> str:
    """Decode a base64 cursor.

    Args:
        cursor: Base64 encoded cursor.

    Returns:
        str: Decoded cursor value.

    Raises:
        ValueError: If cursor is invalid.
    """
    try:
        return base64.urlsafe_b64decode(cursor.encode()).decode()
    except Exception as e:
        raise ValueError(f"Invalid cursor: {cursor}") from e


@dataclass(frozen=True, slots=True)
class CursorPaginationParams:
    """Parameters for cursor-based pagination."""

    cursor: str | None = None
    limit: int = 20

    def __post_init__(self) -> None:
        """Validate pagination parameters."""
        if self.limit < 1:
            object.__setattr__(self, "limit", 1)
        if self.limit > 100:
            object.__setattr__(self, "limit", 100)


@dataclass(frozen=True, slots=True)
class CursorPaginationResult[T]:
    """Result of cursor-based pagination."""

    items: Sequence[T]
    next_cursor: str | None
    has_more: bool
