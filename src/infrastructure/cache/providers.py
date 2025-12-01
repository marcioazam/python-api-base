"""Cache provider implementations with PEP 695 generics.

**Feature: enterprise-features-2025, Task 1.1: Enhance CacheProvider Protocol**
**Validates: Requirements 1.1, 1.8, 1.9**
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from abc import abstractmethod
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from .config import CacheConfig

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class CacheEntry[T]:
    """A single cache entry with expiration tracking.

    PEP 695 generic dataclass for type-safe cache entries.

    Attributes:
        key: The cache key.
        value: The cached value of type T.
        created_at: When entry was created.
        ttl: Time-to-live in seconds. None for no expiration.
        expires_at: When entry expires. None for no expiration.
    """

    key: str
    value: T
    created_at: datetime
    ttl: int | None = None
    expires_at: datetime | None = None

    @property
    def is_expired(self) -> bool:
        """Check if this entry has expired."""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at


@dataclass(frozen=True, slots=True)
class CacheStats:
    """Cache statistics for monitoring.

    Attributes:
        hits: Number of cache hits.
        misses: Number of cache misses.
        hit_rate: Ratio of hits to total requests.
        memory_usage_bytes: Estimated memory usage.
        entry_count: Number of entries in cache.
    """

    hits: int
    misses: int
    hit_rate: float
    memory_usage_bytes: int
    entry_count: int


class CacheProvider[T](Protocol):
    """Protocol for cache providers with PEP 695 generics.

    Type-safe interface for cache operations.
    """

    @abstractmethod
    async def get(self, key: str) -> T | None:
        """Retrieve a value from the cache."""
        ...

    @abstractmethod
    async def set(self, key: str, value: T, ttl: int | None = None) -> None:
        """Store a value in the cache."""
        ...

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Remove a value from the cache. Returns True if key existed."""
        ...

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if a key exists in the cache."""
        ...

    @abstractmethod
    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern. Returns count of deleted keys."""
        ...

    @abstractmethod
    async def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        ...


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

    Attributes:
        hit_rate: Current cache hit rate (0.0 to 1.0)
        hits: Total number of cache hits
        misses: Total number of cache misses

    Example:
        >>> cache = InMemoryCacheProvider[dict](CacheConfig(max_size=1000, ttl=300))
        >>> await cache.set("user:123", {"name": "John"})
        >>> user = await cache.get("user:123")
        >>> print(f"Hit rate: {cache.hit_rate:.2%}")
    """

    def __init__(self, config: CacheConfig | None = None) -> None:
        """Initialize in-memory cache.

        Args:
            config: Cache configuration. If None, uses default CacheConfig.
        """
        self._config = config or CacheConfig()
        self._cache: OrderedDict[str, CacheEntry[T]] = OrderedDict()
        self._lock = asyncio.Lock()
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    @property
    def hit_rate(self) -> float:
        """Get current cache hit rate.

        Returns:
            Float between 0.0 and 1.0 representing the ratio of hits to total requests.
            Returns 0.0 if no requests have been made.
        """
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
        """Get total number of cache evictions.

        **Feature: api-base-score-100, Task 4.2: Integrate metrics with InMemoryCacheProvider**
        **Validates: Requirements 3.5**
        """
        return self._evictions

    def reset_stats(self) -> None:
        """Reset hit/miss/eviction counters to zero."""
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def get_metrics(self) -> "CacheStats":
        """Get cache metrics for OpenTelemetry export.

        **Feature: api-base-score-100, Task 4.2: Integrate metrics with InMemoryCacheProvider**
        **Validates: Requirements 3.5**

        Returns:
            CacheStats with current metrics.
        """
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
        effective_ttl = ttl if ttl is not None else self._config.ttl
        now = datetime.now()
        expires_at = None
        if effective_ttl is not None:
            from datetime import timedelta

            expires_at = now + timedelta(seconds=effective_ttl)

        async with self._lock:
            if full_key not in self._cache and len(self._cache) >= self._config.max_size:
                self._cache.popitem(last=False)
                self._evictions += 1  # Track LRU eviction

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
        import fnmatch

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
                memory_usage_bytes=0,  # Estimation not implemented
                entry_count=len(self._cache),
            )

    async def cleanup_expired(self) -> int:
        """Remove all expired entries."""
        async with self._lock:
            expired_keys = [k for k, v in self._cache.items() if v.is_expired]
            for key in expired_keys:
                del self._cache[key]
            return len(expired_keys)

    # =========================================================================
    # Tag-based cache invalidation
    # **Feature: python-api-base-2025-review**
    # **Validates: Requirements 123.3**
    # =========================================================================

    async def set_with_tags(
        self,
        key: str,
        value: T,
        tags: list[str],
        ttl: int | None = None,
    ) -> None:
        """Store a value with associated tags for group invalidation.

        Args:
            key: Cache key.
            value: Value to cache.
            tags: List of tags to associate with this entry.
            ttl: Time-to-live in seconds.
        """
        await self.set(key, value, ttl)

        # Store key-to-tags mapping
        full_key = self._make_key(key)
        async with self._lock:
            if not hasattr(self, "_tag_index"):
                self._tag_index: dict[str, set[str]] = {}

            for tag in tags:
                if tag not in self._tag_index:
                    self._tag_index[tag] = set()
                self._tag_index[tag].add(full_key)

    async def invalidate_by_tag(self, tag: str) -> int:
        """Invalidate all cache entries with the given tag.

        Args:
            tag: Tag to invalidate.

        Returns:
            Number of entries invalidated.
        """
        async with self._lock:
            if not hasattr(self, "_tag_index"):
                self._tag_index = {}
                return 0

            keys_to_delete = self._tag_index.pop(tag, set())
            deleted_count = 0

            for key in keys_to_delete:
                if key in self._cache:
                    del self._cache[key]
                    deleted_count += 1

            # Clean up tag references in other tags
            for other_tag, keys in self._tag_index.items():
                keys.discard(key)

            return deleted_count

    async def get_tags_for_key(self, key: str) -> list[str]:
        """Get all tags associated with a cache key.

        Args:
            key: Cache key.

        Returns:
            List of tags associated with the key.
        """
        full_key = self._make_key(key)
        async with self._lock:
            if not hasattr(self, "_tag_index"):
                return []

            return [tag for tag, keys in self._tag_index.items() if full_key in keys]


class RedisCacheProvider[T]:
    """Redis-based cache with JSON serialization and fallback."""

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        config: CacheConfig | None = None,
        fallback_provider: InMemoryCacheProvider[T] | None = None,
    ) -> None:
        """Initialize Redis cache provider with optional fallback."""
        self._redis_url = redis_url
        self._config = config or CacheConfig()
        self._redis: Any = None
        self._connected = False
        self._fallback = fallback_provider
        self._hits = 0
        self._misses = 0

    async def _get_client(self) -> Any | None:
        """Get or create Redis client."""
        if self._redis is not None and self._connected:
            return self._redis

        try:
            import redis.asyncio as redis

            self._redis = redis.from_url(
                self._redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            await self._redis.ping()
            self._connected = True
            return self._redis
        except ImportError:
            logger.warning("redis package not installed, using fallback")
            self._connected = False
            return None
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}, using fallback")
            self._connected = False
            return None

    def _make_key(self, key: str) -> str:
        """Create full cache key with prefix."""
        if self._config.key_prefix:
            return f"{self._config.key_prefix}:{key}"
        return key

    def _serialize(self, value: T) -> str:
        """Serialize value to JSON string."""
        return json.dumps(value, default=str)

    def _deserialize(self, data: str | None) -> T | None:
        """Deserialize JSON string to value."""
        if data is None:
            return None
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            return None

    async def get(self, key: str) -> T | None:
        """Retrieve a value from Redis cache with fallback."""
        client = await self._get_client()
        if client is None and self._fallback:
            return await self._fallback.get(key)
        if client is None:
            return None

        try:
            full_key = self._make_key(key)
            data = await client.get(full_key)
            result = self._deserialize(data)
            if result is not None:
                self._hits += 1
            else:
                self._misses += 1
            return result
        except Exception as e:
            logger.warning(f"Redis get failed: {e}")
            if self._fallback:
                return await self._fallback.get(key)
            return None

    async def set(self, key: str, value: T, ttl: int | None = None) -> None:
        """Store a value in Redis cache with fallback."""
        client = await self._get_client()
        if client is None and self._fallback:
            await self._fallback.set(key, value, ttl)
            return
        if client is None:
            return

        try:
            full_key = self._make_key(key)
            data = self._serialize(value)
            effective_ttl = ttl if ttl is not None else self._config.ttl

            if effective_ttl is not None:
                await client.setex(full_key, effective_ttl, data)
            else:
                await client.set(full_key, data)
        except Exception as e:
            logger.warning(f"Redis set failed: {e}")
            if self._fallback:
                await self._fallback.set(key, value, ttl)

    async def delete(self, key: str) -> bool:
        """Remove a value from Redis cache."""
        client = await self._get_client()
        if client is None and self._fallback:
            return await self._fallback.delete(key)
        if client is None:
            return False

        try:
            full_key = self._make_key(key)
            result = await client.delete(full_key)
            return result > 0
        except Exception as e:
            logger.warning(f"Redis delete failed: {e}")
            if self._fallback:
                return await self._fallback.delete(key)
            return False

    async def exists(self, key: str) -> bool:
        """Check if a key exists in Redis cache."""
        client = await self._get_client()
        if client is None and self._fallback:
            return await self._fallback.exists(key)
        if client is None:
            return False

        try:
            full_key = self._make_key(key)
            return await client.exists(full_key) > 0
        except Exception as e:
            logger.warning(f"Redis exists failed: {e}")
            if self._fallback:
                return await self._fallback.exists(key)
            return False

    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern."""
        client = await self._get_client()
        if client is None and self._fallback:
            return await self._fallback.clear_pattern(pattern)
        if client is None:
            return 0

        try:
            full_pattern = self._make_key(pattern)
            cursor = 0
            deleted = 0
            while True:
                cursor, keys = await client.scan(cursor, match=full_pattern, count=100)
                if keys:
                    deleted += await client.delete(*keys)
                if cursor == 0:
                    break
            return deleted
        except Exception as e:
            logger.warning(f"Redis clear_pattern failed: {e}")
            if self._fallback:
                return await self._fallback.clear_pattern(pattern)
            return 0

    async def clear(self) -> None:
        """Clear all values with the configured prefix."""
        pattern = f"{self._config.key_prefix}:*" if self._config.key_prefix else "*"
        await self.clear_pattern(pattern)

    async def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0.0
        return CacheStats(
            hits=self._hits,
            misses=self._misses,
            hit_rate=hit_rate,
            memory_usage_bytes=0,
            entry_count=0,
        )

    async def close(self) -> None:
        """Close Redis connection."""
        if self._redis is not None:
            await self._redis.close()
            self._redis = None
            self._connected = False
