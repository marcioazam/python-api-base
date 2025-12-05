"""CQRS Query Bus infrastructure.

This module provides:
- Query base class for read operations
- QueryBus for dispatching queries to handlers
- Caching support for query results

**Feature: python-api-base-2025-state-of-art**
**Validates: Requirements 2.2**
"""

import logging
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from typing import Any

from application.common.cqrs.exceptions.exceptions import HandlerNotFoundError

logger = logging.getLogger(__name__)


# =============================================================================
# Query Base Class
# =============================================================================


class Query[T](ABC):
    """Base class for CQRS queries.

    Queries represent requests for data without side effects.
    They should be immutable and contain all parameters needed.

    **Feature: advanced-reusability**
    **Validates: Requirements 5.2**

    Type Parameters:
        T: The type of data returned by the query.

    Example:
        >>> class GetUserQuery(Query[User]):
        ...     def __init__(self, user_id: str):
        ...         self.user_id = user_id
        ...
        ...     async def execute(self) -> User:
        ...         # Query execution logic
        ...         pass
    """

    @abstractmethod
    async def execute(self) -> T:
        """Execute the query.

        Returns:
            The query result data.
        """
        ...


# =============================================================================
# Query Handler Types
# =============================================================================

QueryHandler = Callable[[Any], Awaitable[Any]]
"""Type alias for query handler functions.

A query handler is an async function that takes a query and returns the result data.
"""


# =============================================================================
# Query Bus
# =============================================================================


class QueryBus:
    """Dispatches queries to registered handlers.

    Supports caching of query results for performance optimization.

    **Feature: advanced-reusability**
    **Validates: Requirements 5.4**

    Example:
        >>> bus = QueryBus()
        >>> bus.register(GetUserQuery, get_user_handler)
        >>> user = await bus.dispatch(GetUserQuery(user_id="123"))
    """

    def __init__(self) -> None:
        """Initialize query bus."""
        self._handlers: dict[type, QueryHandler] = {}
        self._cache: Any = None

    def register(
        self,
        query_type: type[Query[Any]],
        handler: QueryHandler,
    ) -> None:
        """Register a handler for a query type.

        Args:
            query_type: The query class to handle.
            handler: Async function that handles the query.

        Raises:
            ValueError: If handler is already registered for this type.
        """
        if query_type in self._handlers:
            raise ValueError(f"Handler already registered for {query_type.__name__}")
        self._handlers[query_type] = handler
        logger.debug(f"Registered handler for {query_type.__name__}")

    def unregister(self, query_type: type[Query[Any]]) -> None:
        """Unregister a handler for a query type.

        Args:
            query_type: The query class to unregister.
        """
        self._handlers.pop(query_type, None)
        logger.debug(f"Unregistered handler for {query_type.__name__}")

    def set_cache(self, cache: Any) -> None:
        """Set cache provider for query results.

        Args:
            cache: Cache provider implementing get/set methods.
        """
        self._cache = cache
        logger.debug("Cache provider set for query bus")

    async def dispatch[T](self, query: Query[T]) -> T:
        """Dispatch a query to its registered handler.

        Args:
            query: The query to dispatch.

        Returns:
            Query result from the handler.

        Raises:
            HandlerNotFoundError: If no handler is registered.
        """
        query_type = type(query)
        handler = self._handlers.get(query_type)

        if handler is None:
            raise HandlerNotFoundError(query_type)

        # Check cache if available
        cache_key = self._get_cache_key(query)
        if self._cache is not None and cache_key:
            cached = await self._cache.get(cache_key)
            if cached is not None:
                logger.debug(f"Cache hit for {query_type.__name__}")
                return cached

        # Execute query
        logger.debug(f"Dispatching query {query_type.__name__}")
        result = await handler(query)

        # Cache result if caching is enabled
        if self._cache is not None and cache_key:
            ttl = getattr(query, "cache_ttl", None)
            await self._cache.set(cache_key, result, ttl)
            logger.debug(f"Cached result for {query_type.__name__}")

        return result

    def _get_cache_key(self, query: Query[Any]) -> str | None:
        """Generate cache key for a query.

        Args:
            query: The query to generate key for.

        Returns:
            Cache key string or None if not cacheable.
        """
        if hasattr(query, "cache_key"):
            return query.cache_key

        if not getattr(query, "cacheable", False):
            return None

        query_type = type(query).__name__
        attrs = {k: v for k, v in query.__dict__.items() if not k.startswith("_")}
        return f"{query_type}:{hash(frozenset(attrs.items()))}"
