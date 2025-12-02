"""In-memory cache provider implementation.

**Feature: python-api-base-2025-state-of-art**
**Refactored: 2025 - Extracted from providers.py for SRP compliance**
"""

from __future__ import annotations

import asyncio
import fnmatch
from collections import OrderedDict
from datetime import UTC, datetime, timedelta

from infrastructure.cache.config import CacheConfig
from infrastructure.cache.models import CacheStats
from infrastructure.cache.protocols import CacheEntry


class InMemoryCacheProvider[T]:
    """In-memory cache with LRU eviction and TTL support.

    Thread-safe implementation using asyncio locks.
    Uses OrderedDict for O(1) LRU operations.

    Features:
        - LRU (Least Recently Used) eviction when max_size is reached
        - TTL (Time-To-Live) support for automatic expiration
        - Thread-safe operations with asyncio locks
        - Hit/miss tracking for observability
        - Pattern-based key deletion
        - Tag-based invalidation
    """

    def __init__(self, config: CacheConfig | None = None) -> None:
        """Initialize in-memory cache."""
        self._config = config or CacheConfig()
        self._cache: OrderedDict[str, CacheEntry[T]] = OrderedDict()
        self._lock = asyncio.Lock()
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._tag_index: dict[str, set[str]] = {}

    @property
    def hit_rate(self) -> float:
        """Get current cache hit rate."""
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0

    @property
    def hits(self) -> int:
        """Get total number of cache hits."""
        return self._hits

    @property
    def misses(self) -> int:
        """Get total number of cache misses."""
        return self._misses

    @property
    def evictions(self) -> int:
        """Get total number of cache evictions."""
        return self._evictions

    def reset_stats(self) -> None:
        """Reset hit/miss/eviction counters to zero."""
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def get_metrics(self) -> CacheStats:
        """Get cache metrics for OpenTelemetry export."""
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0.0
        return CacheStats(
            hits=self._hits,
            misses=self._misses,
            hit_rate=hit_rate,
            memory_usage_bytes=0,
            entry_count=len(self._cache),
        )

    def _make_key(self, key: str) -> str:
        """Create full cache key with prefix."""
        if self._config.key_prefix:
            return f"{self._config.key_prefix}:{key}"
        return key

    async def get(self, key: str) -> T | None:
        """Retrieve a value from the cache."""
        full_key = self._make_key(key)

        async with self._lock:
            entry = self._cache.get(full_key)

            if entry is None:
                self._misses += 1
                return None

            if entry.is_expired:
                del self._cache[full_key]
                self._misses += 1
                return None

            self._hits += 1
            self._cache.move_to_end(full_key)
            return entry.value

    async def set(self, key: str, value: T, ttl: int | None = None) -> None:
        """Store a value in the cache."""
        full_key = self._make_key(key)
        effective_ttl = ttl if ttl is not None else self._config.default_ttl
        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=effective_ttl) if effective_ttl else None

        async with self._lock:
            if (
                full_key not in self._cache
                and len(self._cache) >= self._config.max_size
            ):
                self._cache.popitem(last=False)
                self._evictions += 1

            self._cache[full_key] = CacheEntry(
                key=full_key,
                value=value,
                created_at=now,
                ttl=effective_ttl,
                expires_at=expires_at,
            )
            self._cache.move_to_end(full_key)

    async def delete(self, key: str) -> bool:
        """Remove a value from the cache."""
        full_key = self._make_key(key)
        async with self._lock:
            if full_key in self._cache:
                del self._cache[full_key]
                return True
            return False

    async def exists(self, key: str) -> bool:
        """Check if a key exists in the cache."""
        full_key = self._make_key(key)
        async with self._lock:
            entry = self._cache.get(full_key)
            if entry is None:
                return False
            if entry.is_expired:
                del self._cache[full_key]
                return False
            return True

    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern."""
        full_pattern = self._make_key(pattern)
        async with self._lock:
            keys_to_delete = [
                k for k in self._cache.keys() if fnmatch.fnmatch(k, full_pattern)
            ]
            for key in keys_to_delete:
                del self._cache[key]
            return len(keys_to_delete)

    async def clear(self) -> None:
        """Clear all values from the cache."""
        async with self._lock:
            self._cache.clear()

    async def size(self) -> int:
        """Get current cache size."""
        async with self._lock:
            return len(self._cache)

    async def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        async with self._lock:
            total = self._hits + self._misses
            hit_rate = self._hits / total if total > 0 else 0.0
            return CacheStats(
                hits=self._hits,
                misses=self._misses,
                hit_rate=hit_rate,
                memory_usage_bytes=0,
                entry_count=len(self._cache),
            )

    async def cleanup_expired(self) -> int:
        """Remove all expired entries."""
        async with self._lock:
            expired_keys = [k for k, v in self._cache.items() if v.is_expired]
            for key in expired_keys:
                del self._cache[key]
            return len(expired_keys)

    async def set_with_tags(
        self,
        key: str,
        value: T,
        tags: list[str],
        ttl: int | None = None,
    ) -> None:
        """Store a value with associated tags for group invalidation."""
        await self.set(key, value, ttl)

        full_key = self._make_key(key)
        async with self._lock:
            for tag in tags:
                if tag not in self._tag_index:
                    self._tag_index[tag] = set()
                self._tag_index[tag].add(full_key)

    async def invalidate_by_tag(self, tag: str) -> int:
        """Invalidate all cache entries with the given tag."""
        async with self._lock:
            keys_to_delete = self._tag_index.pop(tag, set())
            deleted_count = 0

            for key in keys_to_delete:
                if key in self._cache:
                    del self._cache[key]
                    deleted_count += 1

            for other_tag, keys in self._tag_index.items():
                keys.discard(key)

            return deleted_count

    async def get_tags_for_key(self, key: str) -> list[str]:
        """Get all tags associated with a cache key."""
        full_key = self._make_key(key)
        async with self._lock:
            return [tag for tag, keys in self._tag_index.items() if full_key in keys]
