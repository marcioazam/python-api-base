"""DataLoader for N+1 query prevention.

**Feature: python-api-base-2025-generics-audit**
**Validates: Requirements 20.5**
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass


@dataclass
class DataLoaderConfig:
    """DataLoader configuration."""

    batch_size: int = 100
    cache: bool = True


class DataLoader[TKey, TValue]:
    """Generic DataLoader for N+1 prevention.

    Type Parameters:
        TKey: The key type for loading.
        TValue: The value type returned.

    **Feature: python-api-base-2025-generics-audit**
    **Validates: Requirements 20.5**
    """

    def __init__(
        self,
        batch_fn: Callable[[list[TKey]], Awaitable[list[TValue | None]]],
        config: DataLoaderConfig | None = None,
    ) -> None:
        self._batch_fn = batch_fn
        self._config = config or DataLoaderConfig()
        self._cache: dict[TKey, TValue] = {}
        self._queue: list[TKey] = []
        self._pending: dict[TKey, list[Callable[[TValue | None], None]]] = {}

    async def load(self, key: TKey) -> TValue | None:
        """Load a single value by key.

        Args:
            key: The key to load.

        Returns:
            The loaded value or None.
        """
        if self._config.cache and key in self._cache:
            return self._cache[key]

        self._queue.append(key)

        if len(self._queue) >= self._config.batch_size:
            await self._dispatch()

        return self._cache.get(key)

    async def load_many(self, keys: list[TKey]) -> list[TValue | None]:
        """Load multiple values by keys.

        Args:
            keys: The keys to load.

        Returns:
            List of loaded values (or None for missing).
        """
        results: list[TValue | None] = []
        for key in keys:
            result = await self.load(key)
            results.append(result)
        return results

    async def _dispatch(self) -> None:
        """Dispatch batch load."""
        if not self._queue:
            return

        keys = list(self._queue)
        self._queue.clear()

        values = await self._batch_fn(keys)

        for key, value in zip(keys, values, strict=False):
            if value is not None and self._config.cache:
                self._cache[key] = value

    def clear(self, key: TKey | None = None) -> None:
        """Clear cache for key or all."""
        if key is None:
            self._cache.clear()
        elif key in self._cache:
            del self._cache[key]

    def prime(self, key: TKey, value: TValue) -> None:
        """Prime cache with a value."""
        self._cache[key] = value
