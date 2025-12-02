"""Redis cache provider implementation.

**Feature: python-api-base-2025-state-of-art**
**Refactored: 2025 - Extracted from providers.py for SRP compliance**
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from infrastructure.cache.config import CacheConfig
from infrastructure.cache.models import CacheStats

if TYPE_CHECKING:
    from infrastructure.cache.providers.memory import InMemoryCacheProvider

logger = logging.getLogger(__name__)


class RedisCacheProvider[T]:
    """Redis-based cache with JSON serialization and fallback.

    Features:
        - JSON serialization for complex types
        - Automatic fallback to in-memory cache on connection failure
        - TTL support
        - Pattern-based key deletion
        - Hit/miss tracking
    """

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
            effective_ttl = ttl if ttl is not None else self._config.default_ttl

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
