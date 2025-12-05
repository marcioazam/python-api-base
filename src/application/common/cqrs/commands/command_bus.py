"""CQRS Command Bus infrastructure.

This module provides:
- Command base class for write operations
- CommandBus for dispatching commands to handlers
- Middleware support for cross-cutting concerns
- Domain event emission after command execution

**Feature: python-api-base-2025-state-of-art**
**Validates: Requirements 2.1, 2.2, 2.3**
"""

import logging
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from typing import Any

from application.common.cqrs.exceptions.exceptions import HandlerNotFoundError
from core.base.patterns.result import Ok, Result

logger = logging.getLogger(__name__)


# =============================================================================
# Command Base Class
# =============================================================================


class Command[T, E](ABC):
    """Base class for CQRS commands.

    Commands represent intentions to change the system state.
    They should be immutable and contain all data needed for execution.

    **Feature: advanced-reusability**
    **Validates: Requirements 5.1**

    Type Parameters:
        T: The success result type.
        E: The error type.

    Example:
        >>> class CreateUserCommand(Command[User, UserError]):
        ...     def __init__(self, name: str, email: str):
        ...         self.name = name
        ...         self.email = email
        ...
        ...     async def execute(self) -> Result[User, UserError]:
        ...         # Command execution logic
        ...         pass
    """

    @abstractmethod
    async def execute(self) -> Result[T, E]:
        """Execute the command.

        Returns:
            Result containing success value or error.
        """
        ...


# =============================================================================
# Command Handler Types
# =============================================================================

CommandHandler = Callable[[Any], Awaitable[Any]]
"""Type alias for command handler functions.

A command handler is an async function that takes a command and returns a Result.
"""

MiddlewareFunc = Callable[[Any, Callable[..., Awaitable[Any]]], Awaitable[Any]]
"""Type alias for middleware functions.

Middleware wraps command execution for cross-cutting concerns like logging,
validation, and transaction management.
"""


# =============================================================================
# Command Bus
# =============================================================================


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
        self._middleware: list[MiddlewareFunc] = []
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
            raise ValueError(f"Handler already registered for {command_type.__name__}")
        self._handlers[command_type] = handler
        logger.debug(f"Registered handler for {command_type.__name__}")

    def unregister(self, command_type: type[Command[Any, Any]]) -> None:
        """Unregister a handler for a command type.

        Args:
            command_type: The command class to unregister.
        """
        self._handlers.pop(command_type, None)
        logger.debug(f"Unregistered handler for {command_type.__name__}")

    def add_middleware(self, middleware: MiddlewareFunc) -> None:
        """Add middleware to the command pipeline.

        Middleware is executed in order before the handler.

        Args:
            middleware: Async function (command, next) -> result.
        """
        self._middleware.append(middleware)
        logger.debug("Added middleware to command bus")

    def add_transaction_middleware(self, uow_factory: Callable[[], Any]) -> None:
        """Add transaction middleware for automatic UoW management.

        Args:
            uow_factory: Factory function that creates UoW instances.

        Note:
            This method provides a hook for transaction management.
            Implement custom middleware using add_middleware() for UoW handling.
        """
        async def transaction_middleware(
            command: Any,
            next_handler: Callable[..., Awaitable[Any]],
        ) -> Any:
            """Wrap command execution with UoW transaction."""
            uow = uow_factory()
            try:
                result = await next_handler(command)
                await uow.commit()
                return result
            except Exception:
                await uow.rollback()
                raise
            finally:
                await uow.close()

        self._middleware.append(transaction_middleware)
        logger.debug("Added transaction middleware to command bus")

    def on_event(self, handler: Callable[[Any], Any]) -> None:
        """Register an event handler for domain events.

        Events are emitted after successful command execution.

        Args:
            handler: Async function that handles events.
        """
        self._event_handlers.append(handler)
        logger.debug("Registered event handler")

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
        logger.debug(f"Dispatching command {command_type.__name__}")
        result = await chain(command)

        # Emit events on success
        if isinstance(result, Ok):
            await self._emit_events(command, result.value)

        return result

    def _wrap_middleware(
        self,
        middleware: MiddlewareFunc,
        next_handler: Callable[..., Any],
    ) -> Callable[..., Any]:
        """Wrap a middleware around the next handler."""

        async def wrapped(command: Any) -> Any:
            return await middleware(command, next_handler)

        return wrapped

    async def _emit_events(
        self,
        command: Any,
        result: Any,
        *,
        raise_on_error: bool = False,
    ) -> list[Exception]:
        """Emit domain events after successful command execution.

        Args:
            command: The executed command.
            result: The command result.
            raise_on_error: If True, raises on first handler failure.

        Returns:
            List of exceptions from failed handlers.
        """
        events = getattr(command, "events", None)
        if events is None:
            events = getattr(result, "events", None)

        if not events:
            return []

        errors: list[Exception] = []
        logger.debug(f"Emitting {len(events)} events")

        for event in events:
            event_type = type(event).__name__
            for handler in self._event_handlers:
                handler_name = getattr(handler, "__name__", type(handler).__name__)
                try:
                    await handler(event)
                    logger.debug(f"Event {event_type} handled by {handler_name}")
                except Exception as e:
                    logger.error(
                        f"Event handler {handler_name} failed for {event_type}: {e}",
                        exc_info=True,
                        extra={
                            "event_type": event_type,
                            "handler": handler_name,
                            "operation": "EVENT_EMISSION",
                        },
                    )
                    errors.append(e)
                    if raise_on_error:
                        raise

        return errors
