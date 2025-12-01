"""Cache decorators.

**Feature: code-review-refactoring, Task 17.2: Refactor caching.py**
**Feature: shared-modules-refactoring**
**Validates: Requirements 4.1, 4.2, 4.3, 5.5**
"""

import asyncio
import functools
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from collections.abc import Callable

from .providers import InMemoryCacheProvider
from .utils import generate_cache_key

logger = logging.getLogger(__name__)

_default_cache: InMemoryCacheProvider | None = None
_thread_pool: ThreadPoolExecutor | None = None

CACHE_OPERATION_TIMEOUT = 5.0  # seconds


def get_default_cache() -> InMemoryCacheProvider:
    """Get or create the default in-memory cache."""
    global _default_cache
    if _default_cache is None:
        _default_cache = InMemoryCacheProvider()
    return _default_cache


def _get_thread_pool() -> ThreadPoolExecutor:
    """Get or create the thread pool for sync cache operations."""
    global _thread_pool
    if _thread_pool is None:
        _thread_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="cache-")
    return _thread_pool


def _run_async_in_thread(coro: Any) -> Any:
    """Run an async coroutine in a new event loop in a thread pool.

    This avoids nested event loop errors when calling async cache
    operations from sync code running in an async context.
    """
    def run_in_new_loop() -> Any:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    pool = _get_thread_pool()
    future = pool.submit(run_in_new_loop)
    return future.result(timeout=CACHE_OPERATION_TIMEOUT)


def cached[T, **P](
    ttl: int | None = 3600,
    key_fn: Callable[..., str] | None = None,
    cache_provider: Any | None = None,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator for caching function results.

    Supports both sync and async functions. When a sync function is called
    from an async context, cache operations are executed in a thread pool
    to avoid nested event loop errors.

    Args:
        ttl: Time-to-live in seconds. None for no expiration.
        key_fn: Custom function to generate cache key.
        cache_provider: Cache provider instance. Uses default if None.

    Returns:
        Decorated function with caching.
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

            # Check if we're in an async context
            try:
                asyncio.get_running_loop()
                in_async_context = True
            except RuntimeError:
                in_async_context = False

            if in_async_context:
                # Use thread pool to avoid nested event loop errors
                try:
                    cached_value = _run_async_in_thread(provider.get(cache_key))
                    if cached_value is not None:
                        return cached_value

                    result = func(*args, **kwargs)
                    _run_async_in_thread(provider.set(cache_key, result, ttl))
                    return result
                except TimeoutError:
                    logger.warning(
                        "Cache operation timed out, executing without cache",
                        extra={"cache_key": cache_key, "timeout": CACHE_OPERATION_TIMEOUT},
                    )
                    return func(*args, **kwargs)
                except Exception as e:
                    logger.warning(
                        "Cache operation failed, executing without cache",
                        extra={"cache_key": cache_key, "error": str(e)},
                    )
                    return func(*args, **kwargs)
            else:
                # No async context, safe to use asyncio.run()
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
