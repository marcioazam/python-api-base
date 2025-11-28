"""Cache provider implementations.

**Feature: advanced-reusability**
**Validates: Requirements 3.1, 3.4, 3.6, 3.7**
"""

import asyncio
import json
import logging
import time
from collections import OrderedDict
from typing import Any

from .config import CacheConfig, CacheEntry

logger = logging.getLogger(__name__)


class InMemoryCacheProvider:
    """In-memory cache with LRU eviction and TTL support.

    Thread-safe implementation using asyncio locks.
    Uses OrderedDict for O(1) LRU operations.

    **Feature: advanced-reusability**
    **Validates: Requirements 3.1, 3.4**
    """

    def __init__(self, config: CacheConfig | None = None) -> None:
        """Initialize in-memory cache.

        Args:
            config: Cache configuration. Uses defaults if not provided.
        """
        self._config = config or CacheConfig()
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = asyncio.Lock()

    def _make_key(self, key: str) -> str:
        """Create full cache key with prefix."""
        if self._config.key_prefix:
            return f"{self._config.key_prefix}:{key}"
        return key

    async def get(self, key: str) -> Any | None:
        """Retrieve a value from the cache."""
        full_key = self._make_key(key)

        async with self._lock:
            entry = self._cache.get(full_key)

            if entry is None:
                return None

            if entry.is_expired:
                del self._cache[full_key]
                return None

            self._cache.move_to_end(full_key)
            return entry.value

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Store a value in the cache."""
        full_key = self._make_key(key)
        effective_ttl = ttl if ttl is not None else self._config.ttl

        async with self._lock:
            if full_key not in self._cache and len(self._cache) >= self._config.max_size:
                self._cache.popitem(last=False)

            self._cache[full_key] = CacheEntry(
                value=value,
                created_at=time.time(),
                ttl=effective_ttl,
            )
            self._cache.move_to_end(full_key)

    async def delete(self, key: str) -> None:
        """Remove a value from the cache."""
        full_key = self._make_key(key)
        async with self._lock:
            self._cache.pop(full_key, None)

    async def clear(self) -> None:
        """Clear all values from the cache."""
        async with self._lock:
            self._cache.clear()

    async def size(self) -> int:
        """Get current cache size."""
        async with self._lock:
            return len(self._cache)

    async def cleanup_expired(self) -> int:
        """Remove all expired entries."""
        async with self._lock:
            expired_keys = [k for k, v in self._cache.items() if v.is_expired]
            for key in expired_keys:
                del self._cache[key]
            return len(expired_keys)


class RedisCacheProvider:
    """Redis-based cache with JSON serialization.

    Handles connection errors gracefully by logging warnings
    and continuing without cache (graceful degradation).

    **Feature: advanced-reusability**
    **Validates: Requirements 3.1, 3.6, 3.7**
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        config: CacheConfig | None = None,
    ) -> None:
        """Initialize Redis cache provider."""
        self._redis_url = redis_url
        self._config = config or CacheConfig()
        self._redis: Any = None
        self._connected = False

    async def _get_client(self) -> Any:
        """Get or create Redis client."""
        if self._redis is not None:
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
            logger.warning("redis package not installed, cache disabled")
            return None
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
            self._connected = False
            return None

    def _make_key(self, key: str) -> str:
        """Create full cache key with prefix."""
        if self._config.key_prefix:
            return f"{self._config.key_prefix}:{key}"
        return key

    def _serialize(self, value: Any) -> str:
        """Serialize value to JSON string."""
        return json.dumps(value, default=str)

    def _deserialize(self, data: str | None) -> Any | None:
        """Deserialize JSON string to value."""
        if data is None:
            return None
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            return None

    async def get(self, key: str) -> Any | None:
        """Retrieve a value from Redis cache."""
        try:
            client = await self._get_client()
            if client is None:
                return None

            full_key = self._make_key(key)
            data = await client.get(full_key)
            return self._deserialize(data)
        except Exception as e:
            logger.warning(f"Redis get failed: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Store a value in Redis cache."""
        try:
            client = await self._get_client()
            if client is None:
                return

            full_key = self._make_key(key)
            data = self._serialize(value)
            effective_ttl = ttl if ttl is not None else self._config.ttl

            if effective_ttl is not None:
                await client.setex(full_key, effective_ttl, data)
            else:
                await client.set(full_key, data)
        except Exception as e:
            logger.warning(f"Redis set failed: {e}")

    async def delete(self, key: str) -> None:
        """Remove a value from Redis cache."""
        try:
            client = await self._get_client()
            if client is None:
                return

            full_key = self._make_key(key)
            await client.delete(full_key)
        except Exception as e:
            logger.warning(f"Redis delete failed: {e}")

    async def clear(self) -> None:
        """Clear all values with the configured prefix."""
        try:
            client = await self._get_client()
            if client is None:
                return

            pattern = f"{self._config.key_prefix}:*" if self._config.key_prefix else "*"
            cursor = 0
            while True:
                cursor, keys = await client.scan(cursor, match=pattern, count=100)
                if keys:
                    await client.delete(*keys)
                if cursor == 0:
                    break
        except Exception as e:
            logger.warning(f"Redis clear failed: {e}")

    async def close(self) -> None:
        """Close Redis connection."""
        if self._redis is not None:
            await self._redis.close()
            self._redis = None
            self._connected = False
