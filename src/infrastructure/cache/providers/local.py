"""LRU-based in-memory cache with PEP 695 generics.

Uses PEP 695 type parameter syntax (Python 3.12+) for cleaner generic definitions.

**Feature: architecture-validation-fixes-2025**
**Validates: Requirements 10.1, 10.2**
"""

import time
from collections import OrderedDict
from collections.abc import Hashable, Sequence
from threading import Lock


class LRUCache[K: Hashable, V]:
    """Generic LRU cache with type-safe keys and values.

    Type Parameters:
        K: Key type (must be hashable).
        V: Value type.

    Example:
        >>> cache: LRUCache[str, User] = LRUCache(max_size=100)
        >>> cache.set("user:123", user, ttl=3600)
        >>> user = cache.get("user:123")  # type: User | None

    **Feature: architecture-validation-fixes-2025**
    **Validates: Requirements 10.1, 10.2**
    """

    def __init__(self, max_size: int = 1000) -> None:
        """Initialize LRU cache.

        Args:
            max_size: Maximum number of items to cache.
        """
        self._max_size = max_size
        self._cache: OrderedDict[K, tuple[V, float | None]] = OrderedDict()
        self._lock = Lock()
        self._tags: dict[str, set[K]] = {}

    def get(self, key: K) -> V | None:
        """Get value by key.

        Args:
            key: Cache key.

        Returns:
            Cached value or None if not found/expired.
        """
        with self._lock:
            if key not in self._cache:
                return None
            value, expiry = self._cache[key]
            if expiry and time.time() > expiry:
                del self._cache[key]
                return None
            self._cache.move_to_end(key)
            return value

    def set(
        self, key: K, value: V, ttl: int | None = None, tags: list[str] | None = None
    ) -> None:
        """Set value with optional TTL and tags.

        Args:
            key: Cache key.
            value: Value to cache.
            ttl: Time-to-live in seconds.
            tags: Optional tags for bulk invalidation.
        """
        with self._lock:
            expiry = time.time() + ttl if ttl else None
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = (value, expiry)

            # Track tags for invalidation
            if tags:
                for tag in tags:
                    if tag not in self._tags:
                        self._tags[tag] = set()
                    self._tags[tag].add(key)

            while len(self._cache) > self._max_size:
                evicted_key, _ = self._cache.popitem(last=False)
                self._remove_from_tags(evicted_key)

    def get_many(self, keys: Sequence[K]) -> dict[K, V]:
        """Get multiple values by keys.

        Args:
            keys: Sequence of cache keys.

        Returns:
            Dictionary of found keys and values.

        **Feature: architecture-validation-fixes-2025**
        **Validates: Requirements 10.3**
        """
        result: dict[K, V] = {}
        for key in keys:
            value = self.get(key)
            if value is not None:
                result[key] = value
        return result

    def set_many(self, items: dict[K, V], ttl: int | None = None) -> None:
        """Set multiple values.

        Args:
            items: Dictionary of key-value pairs.
            ttl: Time-to-live in seconds for all items.

        **Feature: architecture-validation-fixes-2025**
        **Validates: Requirements 10.3**
        """
        for key, value in items.items():
            self.set(key, value, ttl)

    def delete(self, key: K) -> bool:
        """Delete value by key.

        Args:
            key: Cache key.

        Returns:
            True if deleted, False if not found.
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._remove_from_tags(key)
                return True
            return False

    def invalidate_by_tag(self, tag: str) -> int:
        """Invalidate all entries with a specific tag.

        Args:
            tag: Tag to invalidate.

        Returns:
            Number of entries invalidated.

        **Feature: architecture-validation-fixes-2025**
        **Validates: Requirements 10.4**
        """
        with self._lock:
            if tag not in self._tags:
                return 0

            keys_to_delete = self._tags[tag].copy()
            count = 0

            for key in keys_to_delete:
                if key in self._cache:
                    del self._cache[key]
                    count += 1

            del self._tags[tag]
            return count

    def _remove_from_tags(self, key: K) -> None:
        """Remove key from all tag sets."""
        for tag_keys in self._tags.values():
            tag_keys.discard(key)

    def clear(self) -> None:
        """Clear all cached values."""
        with self._lock:
            self._cache.clear()
            self._tags.clear()

    def size(self) -> int:
        """Get number of cached items."""
        return len(self._cache)

    def keys(self) -> list[K]:
        """Get all cache keys."""
        with self._lock:
            return list(self._cache.keys())


# Type alias for common string-keyed cache
type StringCache[V] = LRUCache[str, V]
