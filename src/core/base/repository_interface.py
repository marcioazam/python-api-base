"""Generic repository interface for CRUD operations.

Uses PEP 695 type parameter syntax (Python 3.12+) for cleaner generic definitions.

**Feature: python-api-base-2025-state-of-art**
**Validates: Requirements 1.1, 1.2, 11.1**
"""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any

from pydantic import BaseModel

from .pagination import CursorPage


class IRepository[
    T: BaseModel,
    CreateT: BaseModel,
    UpdateT: BaseModel,
    IdType: (str, int) = str,
](ABC):
    """Generic repository interface for CRUD operations.

    Provides an abstraction layer for data access with async support.
    Implementations can use any data source (SQL, NoSQL, in-memory, etc.).

    Type Parameters:
        T: Entity type.
        CreateT: DTO type for creating entities.
        UpdateT: DTO type for updating entities.
        IdType: Type of entity ID (str or int), defaults to str.

    **Feature: python-api-base-2025-state-of-art**
    **Validates: Requirements 1.1, 1.2, 11.1**
    """

    @abstractmethod
    async def get_by_id(self, id: IdType) -> T | None:
        """Get entity by ID.

        Args:
            id: Entity identifier.

        Returns:
            Entity if found, None otherwise.
        """
        ...

    @abstractmethod
    async def get_all(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        filters: dict[str, Any] | None = None,
        sort_by: str | None = None,
        sort_order: str = "asc",
    ) -> tuple[Sequence[T], int]:
        """Get paginated list of entities with total count.

        Args:
            skip: Number of items to skip.
            limit: Maximum number of items to return.
            filters: Optional filter criteria.
            sort_by: Field to sort by.
            sort_order: Sort order ("asc" or "desc").

        Returns:
            Tuple of (entities, total_count).
        """
        ...

    @abstractmethod
    async def create(self, data: CreateT) -> T:
        """Create new entity.

        Args:
            data: Entity creation data.

        Returns:
            Created entity with generated ID.
        """
        ...

    @abstractmethod
    async def update(self, id: IdType, data: UpdateT) -> T | None:
        """Update existing entity.

        Args:
            id: Entity identifier.
            data: Update data.

        Returns:
            Updated entity if found, None otherwise.
        """
        ...

    @abstractmethod
    async def delete(self, id: IdType, *, soft: bool = True) -> bool:
        """Delete entity.

        Args:
            id: Entity identifier.
            soft: If True, perform soft delete. If False, hard delete.

        Returns:
            True if entity was deleted, False if not found.
        """
        ...

    @abstractmethod
    async def create_many(self, data: Sequence[CreateT]) -> Sequence[T]:
        """Bulk create entities.

        Args:
            data: List of entity creation data.

        Returns:
            List of created entities.
        """
        ...

    @abstractmethod
    async def exists(self, id: IdType) -> bool:
        """Check if entity exists.

        Args:
            id: Entity identifier.

        Returns:
            True if entity exists, False otherwise.
        """
        ...

    async def get_page(
        self,
        cursor: str | None = None,
        limit: int = 20,
        filters: dict[str, Any] | None = None,
    ) -> CursorPage[T, str]:
        """Get a page of entities using cursor-based pagination.

        Default implementation using offset pagination. Implementations
        should override this for true cursor-based pagination.

        Args:
            cursor: Opaque cursor from previous page.
            limit: Maximum items per page.
            filters: Optional filter criteria.

        Returns:
            CursorPage with items and navigation cursors.
        """
        # Default implementation using offset pagination
        items, total = await self.get_all(skip=0, limit=limit + 1, filters=filters)
        has_more = len(items) > limit
        items = items[:limit]

        next_cursor = None
        if has_more and items:
            # Simple cursor based on last item
            last = items[-1]
            if hasattr(last, "id"):
                next_cursor = str(last.id)

        return CursorPage(
            items=items,
            next_cursor=next_cursor,
            prev_cursor=cursor,
            has_more=has_more,
        )
