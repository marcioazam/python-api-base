"""Generic infrastructure protocols with PEP 695 type parameters.

**Feature: infrastructure-generics-review-2025**
**Validates: Requirements 1.1, 1.2, 1.3, 1.4**

Provides type-safe protocols for common infrastructure patterns:
- Repository: CRUD operations for entities
- Service: Business logic execution
- Factory: Instance creation
- Store: Key-value storage
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from core.base.patterns.result import Result


@runtime_checkable
class Repository[TEntity, TId](Protocol):
    """Generic repository protocol for CRUD operations.

    Type Parameters:
        TEntity: The entity type managed by this repository.
        TId: The identifier type for entities.

    Example:
        >>> class UserRepository(Repository[User, UUID]):
        ...     def get(self, id: UUID) -> User | None: ...
        ...     def get_all(self) -> list[User]: ...
        ...     def create(self, entity: User) -> User: ...
        ...     def update(self, entity: User) -> User: ...
        ...     def delete(self, id: UUID) -> bool: ...
        ...     def exists(self, id: UUID) -> bool: ...
    """

    def get(self, id: TId) -> TEntity | None:
        """Retrieve an entity by its identifier."""
        ...

    def get_all(self) -> list[TEntity]:
        """Retrieve all entities."""
        ...

    def create(self, entity: TEntity) -> TEntity:
        """Create a new entity."""
        ...

    def update(self, entity: TEntity) -> TEntity:
        """Update an existing entity."""
        ...

    def delete(self, id: TId) -> bool:
        """Delete an entity by its identifier. Returns True if deleted."""
        ...

    def exists(self, id: TId) -> bool:
        """Check if an entity exists."""
        ...


@runtime_checkable
class AsyncRepository[TEntity, TId](Protocol):
    """Async generic repository protocol for CRUD operations.

    Type Parameters:
        TEntity: The entity type managed by this repository.
        TId: The identifier type for entities.
    """

    async def get(self, id: TId) -> TEntity | None:
        """Retrieve an entity by its identifier."""
        ...

    async def get_all(self) -> list[TEntity]:
        """Retrieve all entities."""
        ...

    async def create(self, entity: TEntity) -> TEntity:
        """Create a new entity."""
        ...

    async def update(self, entity: TEntity) -> TEntity:
        """Update an existing entity."""
        ...

    async def delete(self, id: TId) -> bool:
        """Delete an entity by its identifier."""
        ...

    async def exists(self, id: TId) -> bool:
        """Check if an entity exists."""
        ...


@runtime_checkable
class Service[TInput, TOutput, TError](Protocol):
    """Generic service protocol for business operations.

    Type Parameters:
        TInput: The input type for the service operation.
        TOutput: The output type on success.
        TError: The error type on failure.

    Example:
        >>> class CreateUserService(Service[CreateUserInput, User, CreateUserError]):
        ...     def execute(
        ...         self, input: CreateUserInput
        ...     ) -> Result[User, CreateUserError]: ...
    """

    def execute(self, input: TInput) -> Result[TOutput, TError]:
        """Execute the service operation."""
        ...


@runtime_checkable
class AsyncService[TInput, TOutput, TError](Protocol):
    """Async generic service protocol for business operations.

    Type Parameters:
        TInput: The input type for the service operation.
        TOutput: The output type on success.
        TError: The error type on failure.
    """

    async def execute(self, input: TInput) -> Result[TOutput, TError]:
        """Execute the service operation asynchronously."""
        ...


@runtime_checkable
class Factory[TConfig, TInstance](Protocol):
    """Generic factory protocol for instance creation.

    Type Parameters:
        TConfig: The configuration type for creating instances.
        TInstance: The type of instances created.

    Example:
        >>> class CacheFactory(Factory[CacheConfig, CacheProvider]):
        ...     def create(self, config: CacheConfig) -> CacheProvider: ...
        ...     def create_default(self) -> CacheProvider: ...
    """

    def create(self, config: TConfig) -> TInstance:
        """Create an instance with the given configuration."""
        ...

    def create_default(self) -> TInstance:
        """Create an instance with default configuration."""
        ...


@runtime_checkable
class Store[TKey, TValue](Protocol):
    """Generic key-value store protocol.

    Type Parameters:
        TKey: The key type for storage.
        TValue: The value type for storage.

    Example:
        >>> class TokenStore(Store[str, Token]):
        ...     async def get(self, key: str) -> Token | None: ...
        ...     async def set(
        ...         self, key: str, value: Token, ttl: int | None = None
        ...     ) -> None: ...
        ...     async def delete(self, key: str) -> bool: ...
        ...     async def exists(self, key: str) -> bool: ...
    """

    async def get(self, key: TKey) -> TValue | None:
        """Retrieve a value by key."""
        ...

    async def set(self, key: TKey, value: TValue, ttl: int | None = None) -> None:
        """Store a value with optional TTL in seconds."""
        ...

    async def delete(self, key: TKey) -> bool:
        """Delete a value by key. Returns True if deleted."""
        ...

    async def exists(self, key: TKey) -> bool:
        """Check if a key exists."""
        ...


@runtime_checkable
class SyncStore[TKey, TValue](Protocol):
    """Synchronous generic key-value store protocol.

    Type Parameters:
        TKey: The key type for storage.
        TValue: The value type for storage.
    """

    def get(self, key: TKey) -> TValue | None:
        """Retrieve a value by key."""
        ...

    def set(self, key: TKey, value: TValue, ttl: int | None = None) -> None:
        """Store a value with optional TTL in seconds."""
        ...

    def delete(self, key: TKey) -> bool:
        """Delete a value by key. Returns True if deleted."""
        ...

    def exists(self, key: TKey) -> bool:
        """Check if a key exists."""
        ...
