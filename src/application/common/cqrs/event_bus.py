"""Domain Event Bus infrastructure.

This module provides:
- EventHandler protocol for typed event handling
- TypedEventBus for publishing domain events
- Subscription management for event handlers
- Proper error propagation with ExceptionGroup

**Feature: python-api-base-2025-state-of-art**
**Validates: Requirements 2.4**
"""

import logging
from typing import Any, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


class EventHandlerError(Exception):
    """Error raised when event handlers fail."""

    def __init__(
        self,
        event_type: str,
        handler_errors: list[tuple[str, Exception]],
    ) -> None:
        """Initialize event handler error.

        Args:
            event_type: Name of the event type.
            handler_errors: List of (handler_name, exception) tuples.
        """
        self.event_type = event_type
        self.handler_errors = handler_errors
        error_count = len(handler_errors)
        super().__init__(f"{error_count} handler(s) failed for event {event_type}")


# =============================================================================
# Typed Event Handler Protocol
# =============================================================================


@runtime_checkable
class EventHandler[TEvent](Protocol):
    """Protocol for typed domain event handlers.

    Type Parameters:
        TEvent: The event type this handler processes.

    **Feature: python-api-base-2025-state-of-art**
    **Validates: Requirements 2.4**
    """

    async def handle(self, event: TEvent) -> None:
        """Handle a domain event.

        Args:
            event: The domain event to handle.
        """
        ...


# =============================================================================
# Typed Event Bus
# =============================================================================


class TypedEventBus[TEvent]:
    """Typed event bus for publishing domain events.

    Type Parameters:
        TEvent: Base event type for this bus.

    **Feature: python-api-base-2025-state-of-art**
    **Validates: Requirements 2.4**

    Example:
        >>> bus = TypedEventBus()
        >>> bus.subscribe(UserCreatedEvent, user_created_handler)
        >>> await bus.publish(UserCreatedEvent(user_id="123"))
    """

    def __init__(self) -> None:
        """Initialize typed event bus."""
        self._handlers: dict[type, list[EventHandler[Any]]] = {}

    def subscribe[T: TEvent](
        self,
        event_type: type[T],
        handler: EventHandler[T],
    ) -> None:
        """Subscribe handler to event type.

        Args:
            event_type: The event type to subscribe to.
            handler: Handler to call when event is published.
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        logger.debug(f"Subscribed handler to {event_type.__name__}")

    def unsubscribe[T: TEvent](
        self,
        event_type: type[T],
        handler: EventHandler[T],
    ) -> None:
        """Unsubscribe handler from event type.

        Args:
            event_type: The event type to unsubscribe from.
            handler: Handler to remove.
        """
        if event_type in self._handlers:
            self._handlers[event_type] = [
                h for h in self._handlers[event_type] if h != handler
            ]
            logger.debug(f"Unsubscribed handler from {event_type.__name__}")

    async def publish(
        self,
        event: TEvent,
        *,
        raise_on_error: bool = True,
    ) -> list[Exception]:
        """Publish event to all subscribed handlers.

        Args:
            event: The event to publish.
            raise_on_error: If True, raises EventHandlerError on failures.
                           If False, returns list of exceptions.

        Returns:
            List of exceptions from failed handlers (empty if all succeeded).

        Raises:
            EventHandlerError: If any handler fails and raise_on_error is True.
        """
        event_type = type(event)
        handlers = self._handlers.get(event_type, [])
        errors: list[tuple[str, Exception]] = []

        for handler in handlers:
            handler_name = type(handler).__name__
            try:
                await handler.handle(event)
                logger.debug(f"Event {event_type.__name__} handled by {handler_name}")
            except Exception as e:
                msg = f"Event handler {handler_name} failed for {event_type.__name__}"
                logger.error(
                    f"{msg}: {e}",
                    exc_info=True,
                    extra={
                        "event_type": event_type.__name__,
                        "handler": handler_name,
                        "operation": "EVENT_HANDLER_ERROR",
                    },
                )
                errors.append((handler_name, e))

        if errors and raise_on_error:
            raise EventHandlerError(
                event_type=event_type.__name__,
                handler_errors=errors,
            )

        return [e for _, e in errors]
