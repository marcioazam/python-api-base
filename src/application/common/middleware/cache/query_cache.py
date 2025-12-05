"""Query cache middleware for QueryBus.

Provides automatic caching of query results with configurable TTL
and cache invalidation strategies.

**Feature: enterprise-features-2025**
**Validates: Requirements 13.1, 13.2**
"""

import hashlib
import json
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class QueryCache(Protocol):
    """Protocol for query cache implementations."""

    async def get(self, key: str) -> Any | None:
        """Get cached result by key."""
        ...

    async def set(self, key: str, value: Any, ttl: int) -> None:
        """Set cached result with TTL in seconds."""
        ...

    async def delete(self, key: str) -> None:
        """Delete cached result."""
        ...

    async def clear(self) -> None:
        """Clear all cached results."""
        ...

    async def clear_pattern(self, pattern: str) -> int:
        """Clear cached results matching pattern.

        Args:
            pattern: Pattern to match keys (supports * wildcard).

        Returns:
            Number of keys cleared.

        Example:
            >>> await cache.clear_pattern("query_cache:GetUserQuery:*")
            >>> await cache.clear_pattern("*user:123*")
        """
        ...


class InMemoryQueryCache:
    """In-memory query cache for development/testing.

    Note: In production, use Redis or another distributed cache
    to ensure cache consistency across multiple instances.
    """

    def __init__(self) -> None:
        self._cache: dict[str, tuple[Any, datetime]] = {}

    async def get(self, key: str) -> Any | None:
        """Get cached result."""
        if key not in self._cache:
            return None

        value, expires_at = self._cache[key]
        if datetime.now(UTC) > expires_at:
            del self._cache[key]
            return None

        return value

    async def set(self, key: str, value: Any, ttl: int) -> None:
        """Set cached result."""
        expires_at = datetime.now(UTC) + timedelta(seconds=ttl)
        self._cache[key] = (value, expires_at)

    async def delete(self, key: str) -> None:
        """Delete cached result."""
        self._cache.pop(key, None)

    async def clear(self) -> None:
        """Clear all cached results."""
        self._cache.clear()

    def cleanup(self) -> int:
        """Remove expired entries. Returns count of removed entries."""
        now = datetime.now(UTC)
        expired = [k for k, (_, exp) in self._cache.items() if now > exp]
        for k in expired:
            del self._cache[k]
        return len(expired)

    def size(self) -> int:
        """Get number of cached entries."""
        return len(self._cache)

    async def clear_pattern(self, pattern: str) -> int:
        """Clear cached results matching pattern.

        Supports * wildcard for pattern matching.
        Optimized for common prefix patterns (e.g., "prefix:*").

        **Feature: application-layer-code-review-fixes**
        **Validates: Requirements F-05**

        Performance Characteristics:
            - Prefix patterns ("prefix:*"): O(n) with fast startswith
            - Complex patterns ("*mid*"): O(n*m) with fnmatch where m is pattern length
            - For caches >10k keys, consider using Redis SCAN for production

        Args:
            pattern: Pattern to match keys (e.g., "query_cache:GetUserQuery:*").

        Returns:
            Number of keys cleared.

        Example:
            >>> await cache.clear_pattern("query_cache:GetUserQuery:*")
            >>> await cache.clear_pattern("*user:123*")
        """
        # Optimization: if pattern ends with * and has no other wildcards,
        # use prefix matching (O(n) but faster than fnmatch)
        if pattern.endswith("*") and "*" not in pattern[:-1] and "?" not in pattern:
            prefix = pattern[:-1]
            matching_keys = [key for key in self._cache if key.startswith(prefix)]
        else:
            import fnmatch
            matching_keys = [key for key in self._cache if fnmatch.fnmatch(key, pattern)]

        for key in matching_keys:
            del self._cache[key]

        return len(matching_keys)


@dataclass(frozen=True, slots=True)
class QueryCacheConfig:
    """Configuration for query cache middleware."""

    ttl_seconds: int = 300  # 5 minutes default
    key_prefix: str = "query_cache"
    enabled: bool = True
    cache_all_queries: bool = False  # If False, only cache queries with cache_key
    log_hits: bool = True
    log_misses: bool = False


class QueryCacheMiddleware:
    """Middleware for caching query results.

    Caches query results to reduce database load and improve response times.
    Cache keys are generated from query type and parameters.

    Queries can opt-in to caching by providing:
    - `cache_key` attribute on the query
    - `get_cache_key()` method on the query
    - Or cache all queries if `cache_all_queries=True`

    Example:
        >>> cache = InMemoryQueryCache()
        >>> cache_mw = QueryCacheMiddleware(cache, QueryCacheConfig(ttl_seconds=300))
        >>> query_bus.add_middleware(cache_mw)

        >>> @dataclass
        ... class GetUserByIdQuery:
        ...     user_id: str
        ...
        ...     def get_cache_key(self) -> str:
        ...         return f"user:{self.user_id}"
    """

    def __init__(
        self,
        cache: QueryCache,
        config: QueryCacheConfig | None = None,
    ) -> None:
        """Initialize query cache middleware.

        Args:
            cache: Cache implementation for storing results.
            config: Cache configuration.
        """
        self._cache = cache
        self._config = config or QueryCacheConfig()

    def _get_query_cache_key(self, query: Any) -> str | None:
        """Extract cache key from query.

        Args:
            query: The query to extract key from.

        Returns:
            Cache key or None if query should not be cached.
        """
        # Try explicit cache_key attribute
        cache_key = getattr(query, "cache_key", None)
        if cache_key:
            return str(cache_key)

        # Try get_cache_key method
        get_key = getattr(query, "get_cache_key", None)
        if callable(get_key):
            return str(get_key())

        # If cache_all_queries is enabled, generate key from query data
        if self._config.cache_all_queries:
            return self._generate_cache_key(query)

        return None

    def _generate_cache_key(self, query: Any) -> str:
        """Generate cache key from query data.

        Uses query type and serialized data to create a deterministic key.

        Args:
            query: The query object.

        Returns:
            Generated cache key.
        """
        query_type = type(query).__name__

        # Serialize query data
        if hasattr(query, "model_dump"):
            query_data = query.model_dump()
        elif hasattr(query, "__dict__"):
            query_data = query.__dict__
        else:
            query_data = {"repr": repr(query)}

        # Create deterministic hash
        data_json = json.dumps(query_data, sort_keys=True)
        data_hash = hashlib.sha256(data_json.encode()).hexdigest()[:16]

        return f"{query_type}:{data_hash}"

    def _build_cache_key(self, query: Any, query_cache_key: str) -> str:
        """Build full cache key with prefix.

        Args:
            query: The query object.
            query_cache_key: The query-specific cache key.

        Returns:
            Full cache key.
        """
        query_type = type(query).__name__
        return f"{self._config.key_prefix}:{query_type}:{query_cache_key}"

    async def __call__(
        self,
        query: Any,
        next_handler: Callable[[Any], Awaitable[Any]],
    ) -> Any:
        """Execute query with caching.

        Args:
            query: The query to execute.
            next_handler: The next handler in the chain.

        Returns:
            Result from handler or cached result.
        """
        if not self._config.enabled:
            return await next_handler(query)

        query_type = type(query).__name__
        query_cache_key = self._get_query_cache_key(query)

        # No cache key - execute normally
        if not query_cache_key:
            return await next_handler(query)

        cache_key = self._build_cache_key(query, query_cache_key)

        # Check for cached result
        cached = await self._cache.get(cache_key)
        if cached is not None:
            if self._config.log_hits:
                logger.info(
                    f"Query cache HIT for {query_type}",
                    extra={
                        "query_type": query_type,
                        "cache_key": query_cache_key,
                        "operation": "QUERY_CACHE_HIT",
                    },
                )
            return cached

        # Cache miss
        if self._config.log_misses:
            logger.debug(
                f"Query cache MISS for {query_type}",
                extra={
                    "query_type": query_type,
                    "cache_key": query_cache_key,
                    "operation": "QUERY_CACHE_MISS",
                },
            )

        # Execute query
        result = await next_handler(query)

        # Cache result
        await self._cache.set(cache_key, result, self._config.ttl_seconds)

        logger.debug(
            f"Cached result for {query_type}",
            extra={
                "query_type": query_type,
                "cache_key": query_cache_key,
                "ttl_seconds": self._config.ttl_seconds,
                "operation": "QUERY_CACHE_SET",
            },
        )

        return result
