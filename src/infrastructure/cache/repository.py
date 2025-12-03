"""Repository caching decorator with automatic invalidation.

**Feature: repository-caching**
**Validates: Requirements for performant data access with automatic cache invalidation**

Provides a decorator that:
- Caches read operations (get_by_id, get_all, exists)
- Invalidates cache on mutations (create, update, delete)
- Uses entity type name for cache key namespacing
- Supports configurable TTL per entity type
"""

import functools
import inspect
import logging
from collections.abc import Callable, Sequence
from typing import Any, TypeVar

from infrastructure.cache.protocols import CacheProvider

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RepositoryCacheConfig:
    """Configuration for repository caching.

    Attributes:
        ttl: Time-to-live in seconds (default: 300 = 5 minutes).
        enabled: Whether caching is enabled (default: True).
        key_prefix: Prefix for all cache keys (default: "repo").
        log_hits: Whether to log cache hits (default: True in debug).
        log_misses: Whether to log cache misses (default: False).
    """

    def __init__(
        self,
        ttl: int = 300,
        enabled: bool = True,
        key_prefix: str = "repo",
        log_hits: bool = False,
        log_misses: bool = False,
    ) -> None:
        self.ttl = ttl
        self.enabled = enabled
        self.key_prefix = key_prefix
        self.log_hits = log_hits
        self.log_misses = log_misses


def _get_entity_name(repository: Any) -> str:
    """Extract entity name from repository class.

    Attempts to extract from:
    1. repository.__class__.__name__ (e.g., "UserRepository" -> "User")
    2. Fallback to class name if pattern doesn't match

    Args:
        repository: The repository instance.

    Returns:
        Entity name for cache key namespacing.
    """
    class_name = repository.__class__.__name__
    if class_name.endswith("Repository"):
        # Remove "Repository" suffix
        return class_name[:-10]
    return class_name


def _make_cache_key(
    prefix: str, entity_name: str, method_name: str, *args: Any, **kwargs: Any
) -> str:
    """Generate cache key for repository method.

    Format: {prefix}:{entity_name}:{method_name}:{arg_hash}

    Args:
        prefix: Cache key prefix (e.g., "repo").
        entity_name: Entity name (e.g., "User").
        method_name: Method name (e.g., "get_by_id").
        *args: Method positional arguments.
        **kwargs: Method keyword arguments.

    Returns:
        Cache key string.
    """
    # For get_by_id, use the ID directly in the key
    if method_name == "get_by_id" and args:
        return f"{prefix}:{entity_name}:{method_name}:{args[0]}"

    # For other methods, use a hash of all args/kwargs
    arg_str = "_".join(str(arg) for arg in args)
    kwarg_str = "_".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
    combined = f"{arg_str}_{kwarg_str}" if kwarg_str else arg_str

    return f"{prefix}:{entity_name}:{method_name}:{combined}"


def _get_invalidation_pattern(prefix: str, entity_name: str) -> str:
    """Get pattern for invalidating all cache entries for an entity type.

    Args:
        prefix: Cache key prefix.
        entity_name: Entity name.

    Returns:
        Pattern string (e.g., "repo:User:*").
    """
    return f"{prefix}:{entity_name}:*"


def cached_repository[R](
    cache_provider: CacheProvider[Any],
    config: RepositoryCacheConfig | None = None,
) -> Callable[[type[R]], type[R]]:
    """Decorator to add caching to repository classes.

    Automatically caches read operations and invalidates on mutations.

    **Read Operations (Cached):**
    - get_by_id
    - get_all
    - exists
    - get_page

    **Write Operations (Invalidate Cache):**
    - create
    - update
    - delete
    - create_many

    Args:
        cache_provider: Cache provider instance (Redis, InMemory, etc.).
        config: Optional configuration (TTL, logging, etc.).

    Returns:
        Decorated repository class with caching.

    Example:
        >>> from infrastructure.cache.providers import InMemoryCacheProvider
        >>> cache = InMemoryCacheProvider()
        >>> config = RepositoryCacheConfig(ttl=600, log_hits=True)
        >>>
        >>> @cached_repository(cache, config)
        ... class UserRepository(IRepository):
        ...     async def get_by_id(self, id: str) -> User | None:
        ...         # This method will be cached
        ...         return await self._fetch_from_db(id)
        ...
        ...     async def update(self, id: str, data: UpdateUser) -> User | None:
        ...         # This method will invalidate cache
        ...         user = await self._update_in_db(id, data)
        ...         return user
    """
    config = config or RepositoryCacheConfig()

    def class_decorator(repository_class: type[R]) -> type[R]:
        # If caching is disabled, return class unchanged
        if not config.enabled:
            return repository_class

        # Methods to cache (read operations)
        cached_methods = {"get_by_id", "get_all", "exists", "get_page"}

        # Methods that invalidate cache (write operations)
        invalidating_methods = {"create", "update", "delete", "create_many"}

        original_methods: dict[str, Callable] = {}

        def _create_cached_method(method_name: str, original_method: Callable) -> Callable:
            """Create cached version of a read method."""

            @functools.wraps(original_method)
            async def cached_wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
                entity_name = _get_entity_name(self)
                # Generate cache key (args already excludes 'self')
                cache_key = _make_cache_key(
                    config.key_prefix, entity_name, method_name, *args, **kwargs
                )

                # Try to get from cache
                try:
                    cached_value = await cache_provider.get(cache_key)
                    if cached_value is not None:
                        if config.log_hits:
                            logger.info(
                                "Repository cache HIT",
                                extra={
                                    "entity": entity_name,
                                    "method": method_name,
                                    "cache_key": cache_key,
                                },
                            )
                        return cached_value
                except Exception as e:
                    logger.warning(
                        "Cache read failed, falling back to database",
                        extra={"cache_key": cache_key, "error": str(e)},
                    )

                # Cache miss - log if configured
                if config.log_misses:
                    logger.debug(
                        "Repository cache MISS",
                        extra={
                            "entity": entity_name,
                            "method": method_name,
                            "cache_key": cache_key,
                        },
                    )

                # Call original method
                result = await original_method(self, *args, **kwargs)

                # Store in cache (only if result is not None)
                if result is not None:
                    try:
                        await cache_provider.set(cache_key, result, config.ttl)
                    except Exception as e:
                        logger.warning(
                            "Cache write failed",
                            extra={"cache_key": cache_key, "error": str(e)},
                        )

                return result

            return cached_wrapper

        def _create_invalidating_method(method_name: str, original_method: Callable) -> Callable:
            """Create version of write method that invalidates cache."""

            @functools.wraps(original_method)
            async def invalidating_wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
                # Call original method first
                result = await original_method(self, *args, **kwargs)

                # Invalidate cache after successful mutation
                entity_name = _get_entity_name(self)
                pattern = _get_invalidation_pattern(config.key_prefix, entity_name)

                try:
                    count = await cache_provider.clear_pattern(pattern)
                    logger.debug(
                        "Cache invalidated after mutation",
                        extra={
                            "entity": entity_name,
                            "method": method_name,
                            "pattern": pattern,
                            "keys_cleared": count,
                        },
                    )
                except Exception as e:
                    logger.warning(
                        "Cache invalidation failed",
                        extra={"pattern": pattern, "error": str(e)},
                    )

                return result

            return invalidating_wrapper

        # Wrap methods
        for attr_name in dir(repository_class):
            if attr_name.startswith("_"):
                continue

            attr = getattr(repository_class, attr_name)
            if not inspect.iscoroutinefunction(attr):
                continue

            # Store original method
            original_methods[attr_name] = attr

            # Wrap cached methods
            if attr_name in cached_methods:
                setattr(
                    repository_class,
                    attr_name,
                    _create_cached_method(attr_name, attr),
                )

            # Wrap invalidating methods
            elif attr_name in invalidating_methods:
                setattr(
                    repository_class,
                    attr_name,
                    _create_invalidating_method(attr_name, attr),
                )

        # Store original methods for testing/debugging
        repository_class._original_methods = original_methods  # type: ignore
        repository_class._cache_config = config  # type: ignore

        return repository_class

    return class_decorator


# Convenience function for manual cache invalidation
async def invalidate_repository_cache(
    cache_provider: CacheProvider[Any],
    entity_name: str,
    key_prefix: str = "repo",
) -> int:
    """Manually invalidate all cache entries for an entity type.

    Useful for external cache invalidation scenarios.

    Args:
        cache_provider: Cache provider instance.
        entity_name: Entity name (e.g., "User").
        key_prefix: Cache key prefix (default: "repo").

    Returns:
        Number of cache keys cleared.

    Example:
        >>> # Invalidate all User cache entries
        >>> count = await invalidate_repository_cache(cache, "User")
        >>> print(f"Cleared {count} User cache entries")
    """
    pattern = _get_invalidation_pattern(key_prefix, entity_name)
    count = await cache_provider.clear_pattern(pattern)
    logger.info(
        "Manual repository cache invalidation",
        extra={
            "entity": entity_name,
            "pattern": pattern,
            "keys_cleared": count,
        },
    )
    return count
