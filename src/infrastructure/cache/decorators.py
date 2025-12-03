"""Cache decorators for use cases.

**Feature: infrastructure-modules-integration-analysis**
**Validates: Requirements 1.4**

Provides decorators for caching use case method results.
"""

from __future__ import annotations

import functools
import hashlib
import json
import logging
from typing import Any, Callable, ParamSpec, TypeVar

P = ParamSpec("P")
T = TypeVar("T")

logger = logging.getLogger(__name__)


def cached(
    key_prefix: str,
    ttl: int = 3600,
    key_builder: Callable[..., str] | None = None,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Cache decorator for use case methods.

    **Feature: infrastructure-modules-integration-analysis**
    **Validates: Requirements 1.4**

    Args:
        key_prefix: Prefix for cache keys
        ttl: Time to live in seconds (default: 1 hour)
        key_builder: Optional function to build cache key from args

    Returns:
        Decorated function with caching

    Example:
        >>> class ItemUseCase:
        ...     @cached("item", ttl=300)
        ...     async def get(self, item_id: str) -> Item:
        ...         return await self.repo.get(item_id)
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        async def wrapper(self: Any, *args: P.args, **kwargs: P.kwargs) -> T:
            # Get redis client from self if available
            redis = getattr(self, "_redis", None) or getattr(self, "redis", None)

            if redis is None:
                # No cache available, execute directly
                return await func(self, *args, **kwargs)

            # Build cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                # Default key builder: prefix:first_arg or prefix:hash(args)
                if args:
                    cache_key = f"{key_prefix}:{args[0]}"
                else:
                    key_data = json.dumps(kwargs, sort_keys=True, default=str)
                    key_hash = hashlib.md5(key_data.encode()).hexdigest()[:8]
                    cache_key = f"{key_prefix}:{key_hash}"

            # Try to get from cache
            try:
                cached_value = await redis.get(cache_key)
                if cached_value is not None:
                    logger.debug("cache_hit", key=cache_key)
                    return cached_value
            except Exception as e:
                logger.warning("cache_get_error", key=cache_key, error=str(e))

            # Cache miss - execute function
            logger.debug("cache_miss", key=cache_key)
            result = await func(self, *args, **kwargs)

            # Store in cache
            try:
                await redis.set(cache_key, result, ttl)
                logger.debug("cache_set", key=cache_key, ttl=ttl)
            except Exception as e:
                logger.warning("cache_set_error", key=cache_key, error=str(e))

            return result

        return wrapper

    return decorator


def invalidate_cache(
    key_prefix: str,
    key_builder: Callable[..., str] | None = None,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator to invalidate cache after method execution.

    **Feature: infrastructure-modules-integration-analysis**
    **Validates: Requirements 1.4**

    Args:
        key_prefix: Prefix for cache keys to invalidate
        key_builder: Optional function to build cache key from args

    Returns:
        Decorated function that invalidates cache after execution

    Example:
        >>> class ItemUseCase:
        ...     @invalidate_cache("item")
        ...     async def update(self, item_id: str, data: dict) -> Item:
        ...         return await self.repo.update(item_id, data)
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        async def wrapper(self: Any, *args: P.args, **kwargs: P.kwargs) -> T:
            # Execute function first
            result = await func(self, *args, **kwargs)

            # Get redis client from self if available
            redis = getattr(self, "_redis", None) or getattr(self, "redis", None)

            if redis is None:
                return result

            # Build cache key to invalidate
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                if args:
                    cache_key = f"{key_prefix}:{args[0]}"
                else:
                    # Can't determine key, skip invalidation
                    return result

            # Invalidate cache
            try:
                await redis.delete(cache_key)
                logger.debug("cache_invalidated", key=cache_key)
            except Exception as e:
                logger.warning("cache_invalidate_error", key=cache_key, error=str(e))

            return result

        return wrapper

    return decorator


# Global default cache instance
_default_cache: Any | None = None


def get_default_cache() -> Any | None:
    """Get the default cache instance.

    Returns:
        Default cache instance or None if not configured.
    """
    return _default_cache


def set_default_cache(cache: Any) -> None:
    """Set the default cache instance.

    Args:
        cache: Cache instance to use as default.
    """
    global _default_cache
    _default_cache = cache


def invalidate_pattern(
    pattern: str,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator to invalidate cache by pattern after method execution.

    **Feature: infrastructure-modules-integration-analysis**
    **Validates: Requirements 1.4**

    Args:
        pattern: Pattern for cache keys to invalidate (e.g., "item:*")

    Returns:
        Decorated function that invalidates cache pattern after execution
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        async def wrapper(self: Any, *args: P.args, **kwargs: P.kwargs) -> T:
            result = await func(self, *args, **kwargs)

            redis = getattr(self, "_redis", None) or getattr(self, "redis", None)

            if redis is None:
                return result

            try:
                deleted = await redis.delete_pattern(pattern)
                logger.debug("cache_pattern_invalidated", pattern=pattern, count=deleted)
            except Exception as e:
                logger.warning("cache_pattern_error", pattern=pattern, error=str(e))

            return result

        return wrapper

    return decorator
