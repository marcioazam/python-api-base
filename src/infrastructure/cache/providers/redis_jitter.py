"""Redis cache provider with TTL jitter and stampede prevention.

**Feature: api-best-practices-review-2025**
**Validates: Requirements 6.2, 6.5, 22.1, 22.3, 22.4, 22.5**

Implements:
- TTL jitter to prevent thundering herd (5-15% random variation)
- Distributed locking for cache stampede prevention
- Probabilistic early expiration (stale-while-revalidate pattern)
- Pattern-based TTL configuration
"""

import asyncio
import json
import logging
import random
from typing import Any, TypeVar
from collections.abc import Awaitable, Callable

from .cache_models import JitterConfig, TTLPattern, CacheStats

logger = logging.getLogger(__name__)

CacheValueT = TypeVar("CacheValueT")


class RedisCacheWithJitter[T]:
    """Redis cache with TTL jitter and stampede prevention.

    **Feature: api-best-practices-review-2025**
    **Validates: Requirements 6.2, 6.5, 22.1, 22.3, 22.4, 22.5**

    Features:
        - Random TTL jitter (5-15%) to prevent thundering herd
        - Distributed locking for cache stampede prevention
        - Probabilistic early expiration for graceful refresh
        - Pattern-based TTL configuration

    Example:
        >>> cache = RedisCacheWithJitter[dict](redis_client)
        >>> await cache.set("user:123", user_data, ttl=300)  # 5 min with jitter
        >>> user = await cache.get_or_compute(
        ...     "user:123",
        ...     compute=lambda: fetch_user(123),
        ...     ttl=300
        ... )
    """

    def __init__(
        self,
        redis_url: str | None = None,
        redis_client: Any = None,
        config: JitterConfig | None = None,
        key_prefix: str = "",
        default_ttl: int = 300,
    ) -> None:
        """Initialize Redis cache with jitter.

        Args:
            redis_url: Redis connection URL (creates new connection).
            redis_client: Existing Redis client to use (preferred).
            config: Jitter configuration.
            key_prefix: Prefix for all cache keys.
            default_ttl: Default TTL in seconds.
            
        Note:
            Either redis_url or redis_client must be provided.
            If redis_client is provided, it takes precedence.
        """
        self._redis_url = redis_url or "redis://localhost:6379"
        self._external_client = redis_client
        self._config = config or JitterConfig()
        self._key_prefix = key_prefix
        self._default_ttl = default_ttl
        self._redis: Any = None
        self._connected = False
        self._stats = CacheStats()
        self._ttl_patterns: list[TTLPattern] = []

    async def _get_client(self) -> Any | None:
        """Get or create Redis client."""
        # Use external client if provided
        if self._external_client is not None:
            # Check if it's a RedisClient wrapper with a client property
            if hasattr(self._external_client, '_client'):
                self._connected = True
                return self._external_client._client
            self._connected = True
            return self._external_client
            
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
            logger.warning("redis package not installed")
            self._connected = False
            return None
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
            self._connected = False
            return None

    def _make_key(self, key: str) -> str:
        """Create full cache key with prefix."""
        if self._key_prefix:
            return f"{self._key_prefix}:{key}"
        return key

    def _apply_jitter(self, base_ttl: int) -> int:
        """Apply random jitter to TTL.

        **Feature: api-best-practices-review-2025**
        **Validates: Requirements 22.1**

        Adds random variation to TTL to prevent thundering herd:
        - Jitter range: 5-15% of base TTL
        - Result is always >= base_ttl (jitter is always positive)

        Args:
            base_ttl: Base TTL in seconds.

        Returns:
            TTL with jitter applied.
        """
        jitter_percent = random.uniform(
            self._config.min_jitter_percent,
            self._config.max_jitter_percent,
        )
        jitter = int(base_ttl * jitter_percent)
        return base_ttl + jitter

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

    def configure_ttl_pattern(self, pattern: TTLPattern) -> None:
        """Configure TTL for a key pattern.

        **Feature: api-best-practices-review-2025**
        **Validates: Requirements 22.5**

        Args:
            pattern: TTL pattern configuration.
        """
        self._ttl_patterns.append(pattern)

    def _get_ttl_for_key(self, key: str) -> int:
        """Get configured TTL for a key based on patterns."""
        for pattern in self._ttl_patterns:
            if self._key_matches_pattern(key, pattern.pattern):
                return pattern.ttl_seconds
        return self._default_ttl

    def _key_matches_pattern(self, key: str, pattern: str) -> bool:
        """Check if key matches pattern (simple glob matching)."""
        import fnmatch
        return fnmatch.fnmatch(key, pattern)

    async def get(self, key: str) -> T | None:
        """Get value from cache.

        Args:
            key: Cache key.

        Returns:
            Cached value or None if not found.
        """
        client = await self._get_client()
        if client is None:
            return None

        try:
            full_key = self._make_key(key)
            data = await client.get(full_key)
            result = self._deserialize(data)

            if result is not None:
                self._stats.hits += 1
            else:
                self._stats.misses += 1

            return result
        except Exception as e:
            logger.warning(f"Redis get failed: {e}")
            return None

    async def set(
        self,
        key: str,
        value: T,
        ttl: int | None = None,
        apply_jitter: bool = True,
    ) -> None:
        """Set value in cache with optional jitter.

        **Feature: api-best-practices-review-2025**
        **Validates: Requirements 22.1**

        Args:
            key: Cache key.
            value: Value to cache.
            ttl: TTL in seconds (uses default if not provided).
            apply_jitter: Whether to apply TTL jitter.
        """
        client = await self._get_client()
        if client is None:
            return

        try:
            full_key = self._make_key(key)
            data = self._serialize(value)
            effective_ttl = ttl if ttl is not None else self._get_ttl_for_key(key)

            if apply_jitter:
                effective_ttl = self._apply_jitter(effective_ttl)
                self._stats.jittered_sets += 1

            await client.setex(full_key, effective_ttl, data)
        except Exception as e:
            logger.warning(f"Redis set failed: {e}")

    async def delete(self, key: str) -> bool:
        """Delete value from cache.

        Args:
            key: Cache key.

        Returns:
            True if key was deleted.
        """
        client = await self._get_client()
        if client is None:
            return False

        try:
            full_key = self._make_key(key)
            result = await client.delete(full_key)
            return result > 0
        except Exception as e:
            logger.warning(f"Redis delete failed: {e}")
            return False

    async def get_or_compute(
        self,
        key: str,
        compute: Callable[[], Awaitable[T]],
        ttl: int | None = None,
        apply_jitter: bool = True,
    ) -> T:
        """Get from cache or compute with stampede prevention.

        **Feature: api-best-practices-review-2025**
        **Validates: Requirements 22.3**

        Uses distributed locking to prevent cache stampede:
        - Only one caller computes on cache miss
        - Other callers wait for the result
        - Automatically handles lock timeout and retry

        Args:
            key: Cache key.
            compute: Async function to compute value if not cached.
            ttl: TTL in seconds.
            apply_jitter: Whether to apply TTL jitter.

        Returns:
            Cached or computed value.
        """
        # Try to get from cache first
        cached = await self.get(key)
        if cached is not None:
            # Check for probabilistic early recomputation
            if await self._should_early_recompute(key):
                # Trigger background recomputation with error handling
                task = asyncio.create_task(
                    self._background_recompute(key, compute, ttl),
                    name=f"cache_recompute:{key}",
                )
                # Prevent unhandled exception warnings
                task.add_done_callback(self._handle_task_exception)
                self._stats.early_recomputes += 1
            return cached

        # Cache miss - acquire lock to prevent stampede
        client = await self._get_client()
        if client is None:
            # Fallback: compute without locking
            return await compute()

        lock_key = f"lock:{self._make_key(key)}"
        lock_timeout = self._config.lock_timeout_seconds

        try:
            # Try to acquire lock
            if await client.set(lock_key, "1", nx=True, ex=lock_timeout):
                try:
                    # We got the lock - compute and cache
                    value = await compute()
                    await self.set(key, value, ttl, apply_jitter)
                    return value
                finally:
                    # Release lock
                    await client.delete(lock_key)
            else:
                # Lock held by another caller - wait and retry
                self._stats.stampede_prevented += 1
                return await self._wait_for_cache(key, compute, ttl, lock_timeout)
        except Exception as e:
            logger.warning(f"get_or_compute failed: {e}")
            # Fallback: compute without caching
            return await compute()

    async def _wait_for_cache(
        self,
        key: str,
        compute: Callable[[], Awaitable[T]],
        ttl: int | None,
        max_wait: int,
    ) -> T:
        """Wait for cache to be populated by another caller.

        **Feature: api-best-practices-review-2025**
        **Validates: Requirements 22.3**
        """
        wait_interval = 0.1  # 100ms
        elapsed = 0.0

        while elapsed < max_wait:
            await asyncio.sleep(wait_interval)
            elapsed += wait_interval

            cached = await self.get(key)
            if cached is not None:
                return cached

        # Timeout - compute ourselves
        logger.warning(f"Cache wait timeout for key: {key}")
        value = await compute()
        await self.set(key, value, ttl, apply_jitter=True)
        return value

    async def _should_early_recompute(self, key: str) -> bool:
        """Check if we should trigger early recomputation.

        **Feature: api-best-practices-review-2025**
        **Validates: Requirements 22.4**

        Implements probabilistic early expiration to refresh cache
        before it expires, preventing thundering herd on expiry.
        """
        client = await self._get_client()
        if client is None:
            return False

        try:
            full_key = self._make_key(key)
            remaining_ttl = await client.ttl(full_key)

            if remaining_ttl < 0:
                return False

            # Check if within early recompute window
            if remaining_ttl <= self._config.early_recompute_window:
                # Probabilistic trigger to avoid all callers recomputing
                return random.random() < self._config.early_recompute_probability

            return False
        except Exception:
            return False

    async def _background_recompute(
        self,
        key: str,
        compute: Callable[[], Awaitable[T]],
        ttl: int | None,
    ) -> None:
        """Background task to recompute cache entry.

        **Feature: api-best-practices-review-2025**
        **Validates: Requirements 22.4**
        """
        try:
            value = await compute()
            await self.set(key, value, ttl, apply_jitter=True)
            logger.debug(f"Background recompute completed for key: {key}")
        except Exception as e:
            logger.warning(f"Background recompute failed for key {key}: {e}")

    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern.

        Args:
            pattern: Key pattern (glob style).

        Returns:
            Number of keys deleted.
        """
        client = await self._get_client()
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
            return 0

    def _handle_task_exception(self, task: asyncio.Task[None]) -> None:
        """Handle exceptions from background tasks.
        
        Prevents 'Task exception was never retrieved' warnings.
        """
        if task.cancelled():
            return
        exception = task.exception()
        if exception is not None:
            logger.warning(
                f"Background task {task.get_name()} failed: {exception}",
                exc_info=exception,
            )

    def get_stats(self) -> CacheStats:
        """Get cache statistics.

        **Feature: api-best-practices-review-2025**
        **Validates: Requirements 22.6**
        """
        return self._stats

    def reset_stats(self) -> None:
        """Reset cache statistics."""
        self._stats = CacheStats()

    async def close(self) -> None:
        """Close Redis connection."""
        if self._redis is not None:
            await self._redis.close()
            self._redis = None
            self._connected = False
