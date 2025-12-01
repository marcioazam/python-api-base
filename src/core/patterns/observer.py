"""Generic Observer pattern implementation.

Provides type-safe observer pattern with predicate-based filtering.
Uses PEP 695 type parameter syntax.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from typing import Any, Protocol
from weakref import WeakSet

logger = logging.getLogger(__name__)


class Observer[TEvent](Protocol):
    """Protocol for event observers.

    Type Parameters:
        TEvent: The type of events this observer handles.
    """

    async def on_event(self, event: TEvent) -> None:
        """Handle an event.

        Args:
            event: The event to handle.
        """
        ...


class Subject[TEvent]:
    """Subject that notifies observers of events.

    Type Parameters:
        TEvent: The type of events this subject emits.

    Example:
        >>> subject = Subject[OrderEvent]()
        >>> subject.subscribe(order_logger)
        >>> subject.subscribe(inventory_updater, predicate=lambda e: e.type == "created")
        >>> await subject.notify(OrderCreatedEvent(order_id="123"))
    """

    def __init__(self) -> None:
        self._observers: list[tuple[Observer[TEvent], Callable[[TEvent], bool] | None]] = []

    def subscribe(
        self,
        observer: Observer[TEvent],
        predicate: Callable[[TEvent], bool] | None = None,
    ) -> Callable[[], None]:
        """Subscribe an observer to events.

        Args:
            observer: Observer to subscribe.
            predicate: Optional filter function. Observer only receives
                      events where predicate returns True.

        Returns:
            Unsubscribe function.
        """
        entry = (observer, predicate)
        self._observers.append(entry)

        def unsubscribe() -> None:
            if entry in self._observers:
                self._observers.remove(entry)

        return unsubscribe

    def unsubscribe(self, observer: Observer[TEvent]) -> None:
        """Unsubscribe an observer.

        Args:
            observer: Observer to unsubscribe.
        """
        self._observers = [
            (obs, pred) for obs, pred in self._observers if obs is not observer
        ]

    async def notify(self, event: TEvent) -> None:
        """Notify all subscribed observers of an event.

        Args:
            event: Event to send to observers.
        """
        tasks = []
        for observer, predicate in self._observers:
            if predicate is None or predicate(event):
                tasks.append(self._safe_notify(observer, event))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _safe_notify(self, observer: Observer[TEvent], event: TEvent) -> None:
        """Safely notify an observer, catching exceptions."""
        try:
            await observer.on_event(event)
        except Exception as e:
            logger.error(
                "Observer error",
                extra={
                    "observer": type(observer).__name__,
                    "event": type(event).__name__,
                    "error": str(e),
                },
            )

    @property
    def observer_count(self) -> int:
        """Get number of subscribed observers."""
        return len(self._observers)

    def clear(self) -> None:
        """Remove all observers."""
        self._observers.clear()


class FunctionObserver[TEvent]:
    """Observer wrapping an async function.

    Example:
        >>> observer = FunctionObserver(handle_order_event)
        >>> subject.subscribe(observer)
    """

    def __init__(self, handler: Callable[[TEvent], Awaitable[None]]) -> None:
        """Initialize with handler function.

        Args:
            handler: Async function to handle events.
        """
        self._handler = handler

    async def on_event(self, event: TEvent) -> None:
        """Handle event using the wrapped function."""
        await self._handler(event)


class EventBus[TEvent]:
    """Event bus for publishing and subscribing to typed events.

    Supports multiple event types with type-safe handlers.

    Type Parameters:
        TEvent: Base type for all events.

    Example:
        >>> bus = EventBus[DomainEvent]()
        >>> bus.subscribe(OrderCreatedEvent, order_handler)
        >>> bus.subscribe(PaymentReceivedEvent, payment_handler)
        >>> await bus.publish(OrderCreatedEvent(order_id="123"))
    """

    def __init__(self) -> None:
        self._handlers: dict[type, list[Callable[[Any], Awaitable[None]]]] = {}

    def subscribe[TSpecificEvent: TEvent](
        self,
        event_type: type[TSpecificEvent],
        handler: Callable[[TSpecificEvent], Awaitable[None]],
    ) -> Callable[[], None]:
        """Subscribe a handler to a specific event type.

        Args:
            event_type: Type of events to handle.
            handler: Async function to handle events.

        Returns:
            Unsubscribe function.
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

        def unsubscribe() -> None:
            if event_type in self._handlers and handler in self._handlers[event_type]:
                self._handlers[event_type].remove(handler)

        return unsubscribe

    async def publish(self, event: TEvent) -> None:
        """Publish an event to all subscribed handlers.

        Args:
            event: Event to publish.
        """
        event_type = type(event)
        handlers = self._handlers.get(event_type, [])

        tasks = [self._safe_handle(handler, event) for handler in handlers]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _safe_handle(
        self,
        handler: Callable[[Any], Awaitable[None]],
        event: TEvent,
    ) -> None:
        """Safely call a handler, catching exceptions."""
        try:
            await handler(event)
        except Exception as e:
            logger.error(
                "Event handler error",
                extra={
                    "event_type": type(event).__name__,
                    "error": str(e),
                },
            )

    def clear(self) -> None:
        """Remove all handlers."""
        self._handlers.clear()


def observer[TEvent](
    func: Callable[[TEvent], Awaitable[None]]
) -> Observer[TEvent]:
    """Decorator to create an observer from an async function.

    Args:
        func: Async function to wrap.

    Returns:
        Observer wrapping the function.

    Example:
        >>> @observer
        ... async def log_order(event: OrderEvent) -> None:
        ...     logger.info(f"Order event: {event}")
    """
    return FunctionObserver(func)
