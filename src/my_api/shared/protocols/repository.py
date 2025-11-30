"""Repository and infrastructure protocol definitions.

Defines protocols for data access patterns including repositories,
caches, event handlers, CQRS commands/queries, and unit of work.

Feature: file-size-compliance-phase2
"""

from abc import abstractmethod
from typing import Any, Protocol, runtime_checkable
from collections.abc import Sequence
from pydantic import BaseModel


@runtime_checkable
class AsyncRepository[T: BaseModel, CreateDTO: BaseModel, UpdateDTO: BaseModel](Protocol):
    """Protocol for async repository implementations.

    Defines the contract for data access operations. Implementations can use
    any data source (SQL, NoSQL, in-memory, etc.) as long as they implement
    these methods.

    Type Parameters:
        T: Entity type (must be a Pydantic BaseModel).
        CreateDTO: DTO type for creating entities.
        UpdateDTO: DTO type for updating entities.
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

    async def list_all(
        self, skip: int = 0, limit: int = 100
    ) -> Sequence[T]:
        """List entities with pagination.

        Args:
            skip: Number of entities to skip.
            limit: Maximum number of entities to return.

        Returns:
            Sequence of entities.
        """
        ...

@runtime_checkable
class CacheProvider(Protocol):
    """Protocol for cache implementations.

    Defines the contract for cache operations. Implementations can use
    any cache backend (in-memory, Redis, Memcached, etc.).
    """

    async def get(self, key: str) -> Any | None:
        """Retrieve a value from the cache.

        Args:
            key: The cache key.

        Returns:
            The cached value if found and not expired, None otherwise.
        """
        ...

    async def set(
        self, key: str, value: Any, ttl: int | None = None
    ) -> None:
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

@runtime_checkable
class EventHandler[T](Protocol):
    """Protocol for domain event handlers.

    Defines the contract for handling domain events.

    Type Parameters:
        T: The event type this handler processes.
    """

    async def handle(self, event: T) -> None:
        """Handle a domain event.

        Args:
            event: The domain event to handle.
        """
        ...

class Command[ResultT](Protocol):
    """Protocol for CQRS commands.

    Commands represent intentions to change the system state.
    They should be immutable and contain all data needed for execution.

    Type Parameters:
        ResultT: The type of result returned after execution.
    """

    @abstractmethod
    async def execute(self) -> ResultT:
        """Execute the command.

        Returns:
            The result of the command execution.
        """
        ...

class Query[ResultT](Protocol):
    """Protocol for CQRS queries.

    Queries represent requests for data without side effects.
    They should be immutable and contain all parameters needed for the query.

    Type Parameters:
        ResultT: The type of data returned by the query.
    """

    @abstractmethod
    async def execute(self) -> ResultT:
        """Execute the query.

        Returns:
            The query result data.
        """
        ...

@runtime_checkable
class CommandHandler[T, ResultT](Protocol):
    """Protocol for command handlers.

    Command handlers process commands and return results.

    Type Parameters:
        T: The command type this handler processes.
        ResultT: The type of result returned.
    """

    async def handle(self, command: T) -> ResultT:
        """Handle a command.

        Args:
            command: The command to handle.

        Returns:
            The result of handling the command.
        """
        ...

@runtime_checkable
class QueryHandler[T, ResultT](Protocol):
    """Protocol for query handlers.

    Query handlers process queries and return data.

    Type Parameters:
        T: The query type this handler processes.
        ResultT: The type of data returned.
    """

    async def handle(self, query: T) -> ResultT:
        """Handle a query.

        Args:
            query: The query to handle.

        Returns:
            The query result data.
        """
        ...

@runtime_checkable
class Mapper[T, ResultT](Protocol):
    """Protocol for entity mappers.

    Mappers transform entities to DTOs and vice versa.

    Type Parameters:
        T: The source type.
        ResultT: The target type.
    """

    def to_dto(self, entity: T) -> ResultT:
        """Convert an entity to a DTO.

        Args:
            entity: The entity to convert.

        Returns:
            The converted DTO.
        """
        ...

    def to_entity(self, dto: ResultT) -> T:
        """Convert a DTO to an entity.

        Args:
            dto: The DTO to convert.

        Returns:
            The converted entity.
        """
        ...

@runtime_checkable
class UnitOfWork(Protocol):
    """Protocol for Unit of Work pattern.

    Manages transactions and ensures atomic operations.
    """

    async def __aenter__(self) -> "UnitOfWork":
        """Enter the unit of work context."""
        ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Exit the unit of work context."""
        ...

    async def commit(self) -> None:
        """Commit the current transaction."""
        ...

    async def rollback(self) -> None:
        """Rollback the current transaction."""
        ...