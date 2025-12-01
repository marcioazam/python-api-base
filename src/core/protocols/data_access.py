"""Data access protocol definitions.

Defines protocols for data access patterns including repositories,
caches, and unit of work for transaction management.

Feature: file-size-compliance-phase2
"""

from collections.abc import Sequence
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel


@runtime_checkable
class AsyncRepository[T: BaseModel, CreateDTO: BaseModel, UpdateDTO: BaseModel](
    Protocol
):
    """Protocol for async repository implementations.

    Defines the contract for data access operations. Implementations can use
    any data source (SQL, NoSQL, in-memory, etc.) as long as they implement
    these methods.

    Type Parameters:
        T: Entity type (must be a Pydantic BaseModel).
        CreateDTO: DTO type for creating entities.
        UpdateDTO: DTO type for updating entities.

    Feature: file-size-compliance-phase2
    """

    async def get_by_id(self, entity_id: Any) -> T | None:
        """Retrieve an entity by its identifier.

        Args:
            entity_id: The unique identifier of the entity.

        Returns:
            The entity if found, None otherwise.
        """
        ...

    async def create(self, data: CreateDTO) -> T:
        """Create a new entity.

        Args:
            data: The data transfer object containing creation data.

        Returns:
            The created entity with generated ID.
        """
        ...

    async def update(self, entity_id: Any, data: UpdateDTO) -> T | None:
        """Update an existing entity.

        Args:
            entity_id: The unique identifier of the entity.
            data: The data transfer object containing update data.

        Returns:
            The updated entity if found, None otherwise.
        """
        ...

    async def delete(self, entity_id: Any) -> bool:
        """Delete an entity.

        Args:
            entity_id: The unique identifier of the entity.

        Returns:
            True if the entity was deleted, False if not found.
        """
        ...

    async def list_all(self, skip: int = 0, limit: int = 100) -> Sequence[T]:
        """List entities with pagination.

        Args:
            skip: Number of entities to skip.
            limit: Maximum number of entities to return.

        Returns:
            Sequence of entities.
        """
        ...

    async def bulk_create(self, data: Sequence[CreateDTO]) -> Sequence[T]:
        """Create multiple entities in bulk.

        Args:
            data: Sequence of DTOs for creating entities.

        Returns:
            Sequence of created entities.
        """
        ...

    async def bulk_update(
        self, updates: Sequence[tuple[Any, UpdateDTO]]
    ) -> Sequence[T | None]:
        """Update multiple entities in bulk.

        Args:
            updates: Sequence of (entity_id, update_data) tuples.

        Returns:
            Sequence of updated entities (None for not found).
        """
        ...

    async def bulk_delete(self, entity_ids: Sequence[Any]) -> int:
        """Delete multiple entities in bulk.

        Args:
            entity_ids: Sequence of entity identifiers.

        Returns:
            Number of entities deleted.
        """
        ...

    async def exists(self, entity_id: Any) -> bool:
        """Check if an entity exists.

        Args:
            entity_id: The unique identifier of the entity.

        Returns:
            True if entity exists, False otherwise.
        """
        ...

    async def count(self, filters: dict[str, Any] | None = None) -> int:
        """Count entities matching filters.

        Args:
            filters: Optional filters to apply.

        Returns:
            Number of matching entities.
        """
        ...


@runtime_checkable
class CacheProvider(Protocol):
    """Protocol for cache implementations.

    Defines the contract for cache operations. Implementations can use
    any cache backend (in-memory, Redis, Memcached, etc.).

    Feature: file-size-compliance-phase2
    """

    async def get(self, key: str) -> Any | None:
        """Retrieve a value from the cache.

        Args:
            key: The cache key.

        Returns:
            The cached value if found and not expired, None otherwise.
        """
        ...

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Store a value in the cache.

        Args:
            key: The cache key.
            value: The value to cache.
            ttl: Time-to-live in seconds. None for no expiration.
        """
        ...

    async def delete(self, key: str) -> None:
        """Remove a value from the cache.

        Args:
            key: The cache key.
        """
        ...

    async def clear(self) -> None:
        """Clear all values from the cache."""
        ...

    async def get_many(self, keys: Sequence[str]) -> dict[str, Any]:
        """Retrieve multiple values from the cache.

        Args:
            keys: Sequence of cache keys.

        Returns:
            Dictionary mapping keys to values (missing keys omitted).
        """
        ...

    async def set_many(self, items: dict[str, Any], ttl: int | None = None) -> None:
        """Store multiple values in the cache.

        Args:
            items: Dictionary of key-value pairs to cache.
            ttl: Time-to-live in seconds. None for no expiration.
        """
        ...

    async def invalidate_by_tag(self, tag: str) -> int:
        """Invalidate all cache entries with a specific tag.

        Args:
            tag: The tag to invalidate.

        Returns:
            Number of entries invalidated.
        """
        ...


@runtime_checkable
class UnitOfWork(Protocol):
    """Protocol for Unit of Work pattern.

    Manages transactions and ensures atomic operations across repositories.

    Feature: file-size-compliance-phase2
    """

    async def __aenter__(self) -> "UnitOfWork":
        """Enter the unit of work context.

        Returns:
            The unit of work instance.
        """
        ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Exit the unit of work context.

        Automatically rolls back on exception.

        Args:
            exc_type: Exception type if raised.
            exc_val: Exception value if raised.
            exc_tb: Exception traceback if raised.
        """
        ...

    async def commit(self) -> None:
        """Commit the current transaction.

        Makes all changes permanent.
        """
        ...

    async def rollback(self) -> None:
        """Rollback the current transaction.

        Discards all changes made in this unit of work.
        """
        ...
