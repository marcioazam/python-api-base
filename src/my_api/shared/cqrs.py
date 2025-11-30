"""CQRS (Command Query Responsibility Segregation) infrastructure.

This module provides:
- Command and Query base classes
- CommandBus and QueryBus for dispatching
- Handler registration and middleware support
- Domain event emission after command execution

Uses PEP 695 type parameter syntax (Python 3.12+) for cleaner generic definitions.

**Feature: advanced-reusability**
**Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5**
"""

import logging
from abc import ABC, abstractmethod
from typing import Any
from collections.abc import Callable

from my_api.shared.result import Ok, Result

logger = logging.getLogger(__name__)


class Command[T, E](ABC):
    """Base class for CQRS commands.

    Commands represent intentions to change the system state.
    They should be immutable and contain all data needed for execution.

    **Feature: advanced-reusability**
    **Validates: Requirements 5.1**

    Type Parameters:
        T: The success result type.
        E: The error type.
    """

    @abstractmethod
    async def execute(self) -> Result[T, E]:
        """Execute the command.

        Returns:
            Result containing success value or error.
        """
        ...


class Query[T](ABC):
    """Base class for CQRS queries.

    Queries represent requests for data without side effects.
    They should be immutable and contain all parameters needed.

    **Feature: advanced-reusability**
    **Validates: Requirements 5.2**

    Type Parameters:
        T: The type of data returned by the query.
    """

    @abstractmethod
    async def execute(self) -> T:
        """Execute the query.

        Returns:
            The query result data.
        """
        ...


# Handler type aliases
CommandHandler = Callable[[Any], Any]
QueryHandler = Callable[[Any], Any]
Middleware = Callable[[Any, Callable[..., Any]], Any]


class HandlerNotFoundError(Exception):
    """Raised when no handler is registered for a command/query type."""

    def __init__(self, command_type: type) -> None:
        self.command_type = command_type
        super().__init__(f"No handler registered for {command_type.__name__}")


class CommandBus:
    """Dispatches commands to registered handlers.

    Supports middleware for cross-cutting concerns like logging,
    validation, and transaction management.

    **Feature: advanced-reusability**
    **Validates: Requirements 5.3, 5.5**

    Example:
        >>> bus = CommandBus()
        >>> bus.register(CreateUserCommand, create_user_handler)
        >>> result = await bus.dispatch(CreateUserCommand(name="John"))
    """

    def __init__(self) -> None:
        """Initialize command bus."""
        self._handlers: dict[type, CommandHandler] = {}
        self._middleware: list[Middleware] = []
        self._event_handlers: list[Callable[[Any], Any]] = []

    def register(
        self,
        command_type: type[Command[Any, Any]],
        handler: CommandHandler,
    ) -> None:
        """Register a handler for a command type.

        Args:
            command_type: The command class to handle.
            handler: Async function that handles the command.

        Raises:
            ValueError: If handler is already registered for this type.
        """
        if command_type in self._handlers:
            raise ValueError(
                f"Handler already registered for {command_type.__name__}"
            )
        self._handlers[command_type] = handler
        logger.debug(f"Registered handler for {command_type.__name__}")

    def unregister(self, command_type: type[Command[Any, Any]]) -> None:
        """Unregister a handler for a command type.

        Args:
            command_type: The command class to unregister.
        """
        self._handlers.pop(command_type, None)

    def add_middleware(self, middleware: Middleware) -> None:
        """Add middleware to the command pipeline.

        Middleware is executed in order before the handler.

        Args:
            middleware: Async function (command, next) -> result.
        """
        self._middleware.append(middleware)

    def on_event(self, handler: Callable[[Any], Any]) -> None:
        """Register an event handler for domain events.

        Events are emitted after successful command execution.

        Args:
            handler: Async function that handles events.
        """
        self._event_handlers.append(handler)

    async def dispatch[T, E](
        self,
        command: Command[T, E],
    ) -> Result[T, E]:
        """Dispatch a command to its registered handler.

        Args:
            command: The command to dispatch.

        Returns:
            Result from the command handler.

        Raises:
            HandlerNotFoundError: If no handler is registered.
        """
        command_type = type(command)
        handler = self._handlers.get(command_type)

        if handler is None:
            raise HandlerNotFoundError(command_type)

        # Build middleware chain
        async def execute_handler(cmd: Command[T, E]) -> Result[T, E]:
            return await handler(cmd)

        chain = execute_handler
        for middleware in reversed(self._middleware):
            chain = self._wrap_middleware(middleware, chain)

        # Execute command through middleware chain
        result = await chain(command)

        # Emit events on success
        if isinstance(result, Ok):
            await self._emit_events(command, result.value)

        return result

    def _wrap_middleware(
        self,
        middleware: Middleware,
        next_handler: Callable[..., Any],
    ) -> Callable[..., Any]:
        """Wrap a middleware around the next handler."""

        async def wrapped(command: Any) -> Any:
            return await middleware(command, next_handler)

        return wrapped

    async def _emit_events(self, command: Any, result: Any) -> None:
        """Emit domain events after successful command execution."""
        # Check if command has events to emit
        events = getattr(command, "events", None)
        if events is None:
            events = getattr(result, "events", None)

        if events:
            for event in events:
                for handler in self._event_handlers:
                    try:
                        await handler(event)
                    except Exception as e:
                        logger.error(f"Event handler error: {e}")


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
            raise ValueError(
                f"Handler already registered for {query_type.__name__}"
            )
        self._handlers[query_type] = handler
        logger.debug(f"Registered handler for {query_type.__name__}")

    def unregister(self, query_type: type[Query[Any]]) -> None:
        """Unregister a handler for a query type.

        Args:
            query_type: The query class to unregister.
        """
        self._handlers.pop(query_type, None)

    def set_cache(self, cache: Any) -> None:
        """Set cache provider for query results.

        Args:
            cache: Cache provider implementing get/set methods.
        """
        self._cache = cache

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
        result = await handler(query)

        # Cache result if caching is enabled
        if self._cache is not None and cache_key:
            ttl = getattr(query, "cache_ttl", None)
            await self._cache.set(cache_key, result, ttl)

        return result

    def _get_cache_key(self, query: Query[Any]) -> str | None:
        """Generate cache key for a query.

        Args:
            query: The query to generate key for.

        Returns:
            Cache key string or None if not cacheable.
        """
        # Check if query has custom cache key
        if hasattr(query, "cache_key"):
            return query.cache_key

        # Check if query is cacheable
        if not getattr(query, "cacheable", False):
            return None

        # Generate key from query type and attributes
        query_type = type(query).__name__
        attrs = {
            k: v
            for k, v in query.__dict__.items()
            if not k.startswith("_")
        }
        return f"{query_type}:{hash(frozenset(attrs.items()))}"
