"""Cache decorators.

**Feature: advanced-reusability**
**Validates: Requirements 3.5**
"""

import asyncio
import functools
from typing import Any, Callable, ParamSpec

from .providers import InMemoryCacheProvider
from .utils import generate_cache_key

P = ParamSpec("P")

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


def cached[T](
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

            if key_fn is not None:
                cache_key = key_fn(*args, **kwargs)
            else:
                cache_key = generate_cache_key(func, args, kwargs)

            cached_value = await provider.get(cache_key)
            if cached_value is not None:
                return cached_value

            result = await func(*args, **kwargs)
            await provider.set(cache_key, result, ttl)
            return result

        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            provider = cache_provider or get_default_cache()

            if key_fn is not None:
                cache_key = key_fn(*args, **kwargs)
            else:
                cache_key = generate_cache_key(func, args, kwargs)

            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop is not None:
                import warnings

                warnings.warn(
                    "Using @cached on sync function in async context. "
                    "Consider making the function async.",
                    stacklevel=2,
                )
                return func(*args, **kwargs)

            cached_value = asyncio.run(provider.get(cache_key))
            if cached_value is not None:
                return cached_value

            result = func(*args, **kwargs)
            asyncio.run(provider.set(cache_key, result, ttl))
            return result

        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore

    return decorator
