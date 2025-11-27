"""Multi-level caching system with LRU eviction and TTL support.

This module provides a flexible caching infrastructure with:
- In-memory cache with LRU eviction
- Redis cache with JSON serialization
- Configurable TTL (time-to-live)
- Thread-safe async operations
- Graceful degradation on failures

**Feature: advanced-reusability**
**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7**
"""

import asyncio
import functools
import hashlib
import json
import logging
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Callable, ParamSpec, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")
P = ParamSpec("P")


@dataclass
class CacheConfig:
    """Configuration for cache providers.

    Attributes:
        ttl: Default time-to-live in seconds. None for no expiration.
        max_size: Maximum number of entries (for in-memory cache).
        key_prefix: Prefix for all cache keys.
    """

    ttl: int | None = 3600
    max_size: int = 1000
    key_prefix: str = ""


@dataclass
class CacheEntry:
    """A single cache entry with expiration tracking.

    Attributes:
        value: The cached value.
        created_at: Unix timestamp when entry was created.
        ttl: Time-to-live in seconds. None for no expiration.
    """

    value: Any
    created_at: float = field(default_factory=time.time)
    ttl: int | None = None

    @property
    def is_expired(self) -> bool:
        """Check if this entry has expired.

        Returns:
            True if entry has expired, False otherwise.
        """
        if self.ttl is None:
            return False
        return time.time() - self.created_at > self.ttl

    @property
    def remaining_ttl(self) -> int | None:
        """Get remaining TTL in seconds.

        Returns:
            Remaining seconds, 0 if expired, None if no TTL.
        """
        if self.ttl is None:
            return None
        remaining = self.ttl - (time.time() - self.created_at)
        return max(0, int(remaining))


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
        """Create full cache key with prefix.

        Args:
            key: Base cache key.

        Returns:
            Full key with prefix.
        """
        if self._config.key_prefix:
            return f"{self._config.key_prefix}:{key}"
        return key

    async def get(self, key: str) -> Any | None:
        """Retrieve a value from the cache.

        Args:
            key: The cache key.

        Returns:
            The cached value if found and not expired, None otherwise.
        """
        full_key = self._make_key(key)

        async with self._lock:
            entry = self._cache.get(full_key)

            if entry is None:
                return None

            if entry.is_expired:
                del self._cache[full_key]
                return None

            # Move to end for LRU tracking
            self._cache.move_to_end(full_key)
            return entry.value

    async def set(
        self, key: str, value: Any, ttl: int | None = None
    ) -> None:
        """Store a value in the cache.

        Args:
            key: The cache key.
            value: The value to cache.
            ttl: Time-to-live in seconds. Uses config default if None.
        """
        full_key = self._make_key(key)
        effective_ttl = ttl if ttl is not None else self._config.ttl

        async with self._lock:
            # Evict if at capacity and key doesn't exist
            if (
                full_key not in self._cache
                and len(self._cache) >= self._config.max_size
            ):
                # Remove least recently used (first item)
                self._cache.popitem(last=False)

            self._cache[full_key] = CacheEntry(
                value=value,
                created_at=time.time(),
                ttl=effective_ttl,
            )
            # Move to end for LRU tracking
            self._cache.move_to_end(full_key)

    async def delete(self, key: str) -> None:
        """Remove a value from the cache.

        Args:
            key: The cache key.
        """
        full_key = self._make_key(key)

        async with self._lock:
            self._cache.pop(full_key, None)

    async def clear(self) -> None:
        """Clear all values from the cache."""
        async with self._lock:
            self._cache.clear()

    async def size(self) -> int:
        """Get current cache size.

        Returns:
            Number of entries in cache.
        """
        async with self._lock:
            return len(self._cache)

    async def cleanup_expired(self) -> int:
        """Remove all expired entries.

        Returns:
            Number of entries removed.
        """
        async with self._lock:
            expired_keys = [
                k for k, v in self._cache.items() if v.is_expired
            ]
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
        """Initialize Redis cache provider.

        Args:
            redis_url: Redis connection URL.
            config: Cache configuration.
        """
        self._redis_url = redis_url
        self._config = config or CacheConfig()
        self._redis: Any = None
        self._connected = False

    async def _get_client(self) -> Any:
        """Get or create Redis client.

        Returns:
            Redis client or None if connection fails.
        """
        if self._redis is not None:
            return self._redis

        try:
            import redis.asyncio as redis

            self._redis = redis.from_url(
                self._redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            # Test connection
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
        """Create full cache key with prefix.

        Args:
            key: Base cache key.

        Returns:
            Full key with prefix.
        """
        if self._config.key_prefix:
            return f"{self._config.key_prefix}:{key}"
        return key

    def _serialize(self, value: Any) -> str:
        """Serialize value to JSON string.

        Args:
            value: Value to serialize.

        Returns:
            JSON string representation.
        """
        return json.dumps(value, default=str)

    def _deserialize(self, data: str | None) -> Any | None:
        """Deserialize JSON string to value.

        Args:
            data: JSON string or None.

        Returns:
            Deserialized value or None.
        """
        if data is None:
            return None
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            return None

    async def get(self, key: str) -> Any | None:
        """Retrieve a value from Redis cache.

        Args:
            key: The cache key.

        Returns:
            The cached value if found, None otherwise.
        """
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

    async def set(
        self, key: str, value: Any, ttl: int | None = None
    ) -> None:
        """Store a value in Redis cache.

        Args:
            key: The cache key.
            value: The value to cache (must be JSON-serializable).
            ttl: Time-to-live in seconds. Uses config default if None.
        """
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
        """Remove a value from Redis cache.

        Args:
            key: The cache key.
        """
        try:
            client = await self._get_client()
            if client is None:
                return

            full_key = self._make_key(key)
            await client.delete(full_key)
        except Exception as e:
            logger.warning(f"Redis delete failed: {e}")

    async def clear(self) -> None:
        """Clear all values with the configured prefix.

        Warning: This uses SCAN which may be slow on large datasets.
        """
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


def _generate_cache_key(
    func: Callable[..., Any],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> str:
    """Generate a cache key from function and arguments.

    Args:
        func: The function being cached.
        args: Positional arguments.
        kwargs: Keyword arguments.

    Returns:
        A unique cache key string.
    """
    # Create a string representation of the call
    key_parts = [func.__module__, func.__qualname__]

    # Add args (skip self/cls for methods)
    for arg in args:
        try:
            key_parts.append(str(arg))
        except Exception:
            key_parts.append(str(id(arg)))

    # Add sorted kwargs
    for k, v in sorted(kwargs.items()):
        try:
            key_parts.append(f"{k}={v}")
        except Exception:
            key_parts.append(f"{k}={id(v)}")

    # Hash for consistent length
    key_str = ":".join(key_parts)
    return hashlib.sha256(key_str.encode()).hexdigest()[:32]


# Global default cache provider
_default_cache: InMemoryCacheProvider | None = None


def get_default_cache() -> InMemoryCacheProvider:
    """Get or create the default in-memory cache.

    Returns:
        Default InMemoryCacheProvider instance.
    """
    global _default_cache
    if _default_cache is None:
        _default_cache = InMemoryCacheProvider()
    return _default_cache


def cached(
    ttl: int | None = 3600,
    key_fn: Callable[..., str] | None = None,
    cache_provider: Any | None = None,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator for caching function results.

    Supports both sync and async functions. Uses the default
    in-memory cache if no provider is specified.

    **Feature: advanced-reusability**
    **Validates: Requirements 3.5**

    Args:
        ttl: Time-to-live in seconds. None for no expiration.
        key_fn: Custom function to generate cache key from args/kwargs.
        cache_provider: Cache provider instance. Uses default if None.

    Returns:
        Decorated function with caching.

    Example:
        >>> @cached(ttl=300)
        ... async def get_user(user_id: str) -> User:
        ...     return await db.fetch_user(user_id)
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            provider = cache_provider or get_default_cache()

            # Generate cache key
            if key_fn is not None:
                cache_key = key_fn(*args, **kwargs)
            else:
                cache_key = _generate_cache_key(func, args, kwargs)

            # Try to get from cache
            cached_value = await provider.get(cache_key)
            if cached_value is not None:
                return cached_value

            # Execute function and cache result
            result = await func(*args, **kwargs)
            await provider.set(cache_key, result, ttl)
            return result

        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            # For sync functions, run in event loop
            provider = cache_provider or get_default_cache()

            if key_fn is not None:
                cache_key = key_fn(*args, **kwargs)
            else:
                cache_key = _generate_cache_key(func, args, kwargs)

            # Use asyncio.run for sync context
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop is not None:
                # Already in async context - create task
                import warnings
                warnings.warn(
                    "Using @cached on sync function in async context. "
                    "Consider making the function async.",
                    stacklevel=2,
                )
                # Fall through to execute without caching in this edge case
                return func(*args, **kwargs)

            # Check cache
            cached_value = asyncio.run(provider.get(cache_key))
            if cached_value is not None:
                return cached_value

            # Execute and cache
            result = func(*args, **kwargs)
            asyncio.run(provider.set(cache_key, result, ttl))
            return result

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore

    return decorator
