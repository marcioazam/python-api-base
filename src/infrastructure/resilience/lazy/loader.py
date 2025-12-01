"""Lazy loading decorators and batch loader.

**Feature: file-size-compliance-phase2, Task 2.5**
**Validates: Requirements 1.5, 5.1, 5.2, 5.3**
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from functools import wraps

from .proxy import LazyCollection, LazyProxy


def lazy_load[T, **P](func: Callable[P, Awaitable[T]]) -> Callable[P, LazyProxy[T]]:
    """Decorator that wraps an async function to return a LazyProxy."""

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> LazyProxy[T]:
        return LazyProxy(lambda: func(*args, **kwargs))

    return wrapper


def lazy_collection[T, **P](
    func: Callable[P, Awaitable[list[T]]],
) -> Callable[P, LazyCollection[T]]:
    """Decorator that wraps an async function to return a LazyCollection."""

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> LazyCollection[T]:
        return LazyCollection(lambda: func(*args, **kwargs))

    return wrapper


@dataclass
class BatchLoader[T]:
    """Batch loader for preventing N+1 queries."""

    batch_resolver: Callable[[list[str]], Awaitable[dict[str, T]]]
    max_cache_size: int = 10000
    _pending_ids: set[str] = field(default_factory=set, init=False)
    _cache: dict[str, T] = field(default_factory=dict, init=False)

    def add(self, entity_id: str) -> None:
        """Add an ID to the batch."""
        if entity_id not in self._cache:
            self._pending_ids.add(entity_id)

    def add_many(self, entity_ids: list[str]) -> None:
        """Add multiple IDs to the batch."""
        for entity_id in entity_ids:
            self.add(entity_id)

    def _enforce_cache_limit(self) -> None:
        """Evict oldest entries if cache exceeds max size."""
        if len(self._cache) > self.max_cache_size:
            excess = len(self._cache) - self.max_cache_size
            keys_to_remove = list(self._cache.keys())[:excess]
            for key in keys_to_remove:
                del self._cache[key]

    async def load_all(self) -> dict[str, T]:
        """Load all pending entities in a single batch."""
        if self._pending_ids:
            ids_to_load = list(self._pending_ids)
            loaded = await self.batch_resolver(ids_to_load)
            self._cache.update(loaded)
            self._pending_ids.clear()
            self._enforce_cache_limit()
        return self._cache

    async def get(self, entity_id: str) -> T | None:
        """Get a specific entity, loading batch if necessary."""
        if entity_id in self._cache:
            return self._cache[entity_id]

        self.add(entity_id)
        await self.load_all()
        return self._cache.get(entity_id)

    def get_cached(self, entity_id: str) -> T | None:
        """Get an entity only if already cached."""
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
