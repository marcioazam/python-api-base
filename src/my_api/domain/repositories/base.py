"""Base repository protocol for domain layer.

**Feature: domain-code-review-fixes**
**Validates: Requirements 3.1, 3.2, 3.3**
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable


@runtime_checkable
class RepositoryProtocol[T, ID](Protocol):
    """Base repository interface for domain entities.

    This protocol defines the standard CRUD operations that all
    repository implementations should provide.

    Type Parameters:
        T: The entity type this repository manages.
        ID: The identifier type for the entity.

    Example:
        ```python
        class ItemRepository(RepositoryProtocol[Item, str]):
            async def get_by_id(self, id: str) -> Item | None:
                ...
        ```
    """

    async def get_by_id(self, id: ID) -> T | None:
        """Retrieve an entity by its identifier.

        Args:
            id: The unique identifier of the entity.

        Returns:
            The entity if found, None otherwise.
        """
        ...

    async def get_all(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[T]:
        """Retrieve all entities with pagination.

        Args:
            limit: Maximum number of entities to return.
            offset: Number of entities to skip.

        Returns:
            Sequence of entities.
        """
        ...

    async def create(self, entity: T) -> T:
        """Create a new entity.

        Args:
            entity: The entity to create.

        Returns:
            The created entity with generated fields populated.
        """
        ...

    async def update(self, entity: T) -> T:
        """Update an existing entity.

        Args:
            entity: The entity with updated values.

        Returns:
            The updated entity.
        """
        ...

    async def delete(self, id: ID) -> bool:
        """Delete an entity by its identifier.

        Args:
            id: The unique identifier of the entity to delete.

        Returns:
            True if the entity was deleted, False if not found.
        """
        ...


@runtime_checkable
class ReadOnlyRepositoryProtocol[T, ID](Protocol):
    """Read-only repository interface for query operations.

    Use this protocol for repositories that only need read access.
    """

    async def get_by_id(self, id: ID) -> T | None:
        """Retrieve an entity by its identifier."""
        ...

    async def get_all(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[T]:
        """Retrieve all entities with pagination."""
        ...

    async def count(self) -> int:
        """Count total number of entities."""
        ...
