"""Lazy loading proxy for deferred entity loading.

Provides a generic proxy pattern for lazy loading entities from repositories,
reducing unnecessary database queries by deferring loading until first access.

**Feature: api-architecture-analysis, Task 5.1: Lazy Loading Proxy**
**Validates: Requirements 2.1**

Usage:
    from my_api.shared.lazy import LazyProxy, lazy_load

    # Create a lazy proxy for an entity
    user_proxy = LazyProxy(lambda: repository.get_by_id(user_id))

    # Access triggers loading
    user = await user_proxy.get()

    # Or use the decorator
    @lazy_load
    async def get_user_details(user_id: str) -> User:
        return await repository.get_by_id(user_id)
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import Enum, auto
from functools import wraps
from typing import Any, Generic, ParamSpec, TypeVar, overload

T = TypeVar("T")
P = ParamSpec("P")


class LoadState(Enum):
    """State of a lazy-loaded value."""

    NOT_LOADED = auto()
    LOADING = auto()
    LOADED = auto()
    ERROR = auto()


@dataclass
class LazyProxy(Generic[T]):
    """Generic lazy loading proxy for deferred value loading.

    Wraps a loader function and defers execution until the value is
    actually needed. Supports both sync and async loaders.

    Type Parameters:
        T: The type of the value being lazily loaded.

    Attributes:
        loader: Callable that loads the value when invoked.
        _value: Cached value after loading.
        _state: Current loading state.
        _error: Exception if loading failed.

    Example:
        >>> proxy = LazyProxy(lambda: expensive_computation())
        >>> # Value not loaded yet
        >>> result = await proxy.get()  # Now it loads
        >>> result2 = await proxy.get()  # Returns cached value
    """

    loader: Callable[[], T | Awaitable[T]]
    _value: T | None = field(default=None, init=False, repr=False)
    _state: LoadState = field(default=LoadState.NOT_LOADED, init=False)
    _error: Exception | None = field(default=None, init=False, repr=False)

    @property
    def is_loaded(self) -> bool:
        """Check if the value has been loaded."""
        return self._state == LoadState.LOADED

    @property
    def is_loading(self) -> bool:
        """Check if the value is currently being loaded."""
        return self._state == LoadState.LOADING

    @property
    def has_error(self) -> bool:
        """Check if loading resulted in an error."""
        return self._state == LoadState.ERROR

    @property
    def state(self) -> LoadState:
        """Get the current loading state."""
        return self._state

    async def get(self) -> T:
        """Get the value, loading it if necessary.

        Returns:
            The loaded value.

        Raises:
            Exception: If loading fails, re-raises the original exception.
        """
        if self._state == LoadState.LOADED:
            return self._value  # type: ignore

        if self._state == LoadState.ERROR and self._error:
            raise self._error

        self._state = LoadState.LOADING
        try:
            result = self.loader()
            # Handle async loaders
            if isinstance(result, Awaitable):
                self._value = await result
            else:
                self._value = result
            self._state = LoadState.LOADED
            return self._value
        except Exception as e:
            self._state = LoadState.ERROR
            self._error = e
            raise

    def get_sync(self) -> T:
        """Get the value synchronously (for sync loaders only).

        Returns:
            The loaded value.

        Raises:
            RuntimeError: If the loader is async.
            Exception: If loading fails.
        """
        if self._state == LoadState.LOADED:
            return self._value  # type: ignore

        if self._state == LoadState.ERROR and self._error:
            raise self._error

        self._state = LoadState.LOADING
        try:
            result = self.loader()
            if isinstance(result, Awaitable):
                raise RuntimeError("Cannot use get_sync() with async loader")
            self._value = result
            self._state = LoadState.LOADED
            return self._value
        except Exception as e:
            self._state = LoadState.ERROR
            self._error = e
            raise

    def get_if_loaded(self) -> T | None:
        """Get the value only if already loaded.

        Returns:
            The value if loaded, None otherwise.
        """
        if self._state == LoadState.LOADED:
            return self._value
        return None

    def reset(self) -> None:
        """Reset the proxy to unloaded state."""
        self._value = None
        self._state = LoadState.NOT_LOADED
        self._error = None

    def reload(self) -> "LazyProxy[T]":
        """Create a new proxy that will reload the value.

        Returns:
            A new LazyProxy with the same loader but reset state.
        """
        return LazyProxy(self.loader)


@dataclass
class LazyCollection(Generic[T]):
    """Lazy loading collection for deferred batch loading.

    Useful for loading related entities in batches rather than
    one at a time (N+1 query prevention).

    Type Parameters:
        T: The type of items in the collection.
    """

    loader: Callable[[], list[T] | Awaitable[list[T]]]
    _items: list[T] = field(default_factory=list, init=False, repr=False)
    _state: LoadState = field(default=LoadState.NOT_LOADED, init=False)
    _error: Exception | None = field(default=None, init=False, repr=False)

    @property
    def is_loaded(self) -> bool:
        """Check if the collection has been loaded."""
        return self._state == LoadState.LOADED

    async def get_all(self) -> list[T]:
        """Get all items, loading if necessary.

        Returns:
            List of all items.
        """
        if self._state == LoadState.LOADED:
            return self._items

        if self._state == LoadState.ERROR and self._error:
            raise self._error

        self._state = LoadState.LOADING
        try:
            result = self.loader()
            if isinstance(result, Awaitable):
                self._items = await result
            else:
                self._items = result
            self._state = LoadState.LOADED
            return self._items
        except Exception as e:
            self._state = LoadState.ERROR
            self._error = e
            raise

    async def get_first(self) -> T | None:
        """Get the first item, loading if necessary.

        Returns:
            First item or None if empty.
        """
        items = await self.get_all()
        return items[0] if items else None

    async def count(self) -> int:
        """Get the count of items, loading if necessary.

        Returns:
            Number of items.
        """
        items = await self.get_all()
        return len(items)

    def reset(self) -> None:
        """Reset the collection to unloaded state."""
        self._items = []
        self._state = LoadState.NOT_LOADED
        self._error = None


# =============================================================================
# Decorator for Lazy Loading
# =============================================================================


def lazy_load(func: Callable[P, Awaitable[T]]) -> Callable[P, LazyProxy[T]]:
    """Decorator that wraps an async function to return a LazyProxy.

    The decorated function returns a LazyProxy instead of executing
    immediately. The actual function is called when proxy.get() is invoked.

    Args:
        func: Async function to wrap.

    Returns:
        Function that returns a LazyProxy.

    Example:
        >>> @lazy_load
        ... async def get_user(user_id: str) -> User:
        ...     return await repository.get_by_id(user_id)
        ...
        >>> proxy = get_user("123")  # Returns LazyProxy, no DB call yet
        >>> user = await proxy.get()  # Now the DB call happens
    """

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> LazyProxy[T]:
        return LazyProxy(lambda: func(*args, **kwargs))

    return wrapper


def lazy_collection(
    func: Callable[P, Awaitable[list[T]]],
) -> Callable[P, LazyCollection[T]]:
    """Decorator that wraps an async function to return a LazyCollection.

    Args:
        func: Async function that returns a list.

    Returns:
        Function that returns a LazyCollection.

    Example:
        >>> @lazy_collection
        ... async def get_user_orders(user_id: str) -> list[Order]:
        ...     return await order_repo.get_by_user(user_id)
        ...
        >>> orders = get_user_orders("123")  # Returns LazyCollection
        >>> all_orders = await orders.get_all()  # Now loads
    """

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> LazyCollection[T]:
        return LazyCollection(lambda: func(*args, **kwargs))

    return wrapper


# =============================================================================
# Lazy Reference for Related Entities
# =============================================================================


@dataclass
class LazyRef(Generic[T]):
    """Lazy reference to a related entity by ID.

    Useful for representing foreign key relationships without
    immediately loading the related entity.

    Type Parameters:
        T: The type of the referenced entity.

    Example:
        >>> class Order:
        ...     user_id: str
        ...     user: LazyRef[User]
        ...
        >>> order.user = LazyRef("user-123", user_repository.get_by_id)
        >>> user = await order.user.resolve()
    """

    id: str
    resolver: Callable[[str], Awaitable[T | None]]
    _value: T | None = field(default=None, init=False, repr=False)
    _resolved: bool = field(default=False, init=False)

    @property
    def is_resolved(self) -> bool:
        """Check if the reference has been resolved."""
        return self._resolved

    async def resolve(self) -> T | None:
        """Resolve the reference to get the actual entity.

        Returns:
            The resolved entity or None if not found.
        """
        if self._resolved:
            return self._value

        self._value = await self.resolver(self.id)
        self._resolved = True
        return self._value

    def get_if_resolved(self) -> T | None:
        """Get the value only if already resolved.

        Returns:
            The value if resolved, None otherwise.
        """
        return self._value if self._resolved else None

    def reset(self) -> None:
        """Reset the reference to unresolved state."""
        self._value = None
        self._resolved = False


# =============================================================================
# Batch Loader for N+1 Prevention
# =============================================================================


@dataclass
class BatchLoader(Generic[T]):
    """Batch loader for preventing N+1 queries.

    Collects IDs and loads all entities in a single batch query.

    Type Parameters:
        T: The type of entities being loaded.

    Example:
        >>> loader = BatchLoader(repository.get_by_ids)
        >>> loader.add("id1")
        >>> loader.add("id2")
        >>> loader.add("id3")
        >>> entities = await loader.load_all()  # Single query for all IDs
    """

    batch_resolver: Callable[[list[str]], Awaitable[dict[str, T]]]
    _pending_ids: set[str] = field(default_factory=set, init=False)
    _cache: dict[str, T] = field(default_factory=dict, init=False)

    def add(self, entity_id: str) -> None:
        """Add an ID to the batch.

        Args:
            entity_id: ID to add to the pending batch.
        """
        if entity_id not in self._cache:
            self._pending_ids.add(entity_id)

    def add_many(self, entity_ids: list[str]) -> None:
        """Add multiple IDs to the batch.

        Args:
            entity_ids: IDs to add to the pending batch.
        """
        for entity_id in entity_ids:
            self.add(entity_id)

    async def load_all(self) -> dict[str, T]:
        """Load all pending entities in a single batch.

        Returns:
            Dictionary mapping IDs to entities.
        """
        if self._pending_ids:
            ids_to_load = list(self._pending_ids)
            loaded = await self.batch_resolver(ids_to_load)
            self._cache.update(loaded)
            self._pending_ids.clear()
        return self._cache

    async def get(self, entity_id: str) -> T | None:
        """Get a specific entity, loading batch if necessary.

        Args:
            entity_id: ID of the entity to get.

        Returns:
            The entity or None if not found.
        """
        if entity_id in self._cache:
            return self._cache[entity_id]

        self.add(entity_id)
        await self.load_all()
        return self._cache.get(entity_id)

    def get_cached(self, entity_id: str) -> T | None:
        """Get an entity only if already cached.

        Args:
            entity_id: ID of the entity.

        Returns:
            The entity if cached, None otherwise.
        """
        return self._cache.get(entity_id)

    def clear(self) -> None:
        """Clear all pending IDs and cached entities."""
        self._pending_ids.clear()
        self._cache.clear()

    @property
    def pending_count(self) -> int:
        """Number of IDs pending to be loaded."""
        return len(self._pending_ids)

    @property
    def cached_count(self) -> int:
        """Number of entities in cache."""
        return len(self._cache)
