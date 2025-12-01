"""Generic messaging infrastructure with PEP 695 type parameters.

**Feature: python-api-base-2025-state-of-art**
**Validates: Requirements 15.1, 15.2, 15.3**
"""

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any, Protocol, runtime_checkable
import asyncio


# =============================================================================
# Event Bus
# =============================================================================


@runtime_checkable
class EventHandler[TEvent](Protocol):
    """Protocol for typed event handlers.

    Type Parameters:
        TEvent: The event type this handler processes.
    """

    async def handle(self, event: TEvent) -> None:
        """Handle an event."""
        ...


class EventBus[TEvent]:
    """Typed event bus for publishing domain events.

    Type Parameters:
        TEvent: Base event type for this bus.
    """

    def __init__(self) -> None:
        self._handlers: dict[type, list[EventHandler[Any]]] = {}
        self._global_handlers: list[EventHandler[TEvent]] = []

    def subscribe[T: TEvent](
        self,
        event_type: type[T],
        handler: EventHandler[T],
    ) -> None:
        """Subscribe handler to specific event type."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def subscribe_all(self, handler: EventHandler[TEvent]) -> None:
        """Subscribe handler to all events."""
        self._global_handlers.append(handler)

    def unsubscribe[T: TEvent](
        self,
        event_type: type[T],
        handler: EventHandler[T],
    ) -> None:
        """Unsubscribe handler from event type."""
        if event_type in self._handlers:
            self._handlers[event_type] = [
                h for h in self._handlers[event_type] if h != handler
            ]

    async def publish(self, event: TEvent) -> None:
        """Publish event to all subscribed handlers."""
        event_type = type(event)
        handlers = self._handlers.get(event_type, []) + self._global_handlers

        await asyncio.gather(
            *[h.handle(event) for h in handlers],
            return_exceptions=True,
        )


# =============================================================================
# Message Handler
# =============================================================================


@runtime_checkable
class MessageHandler[TMessage, TResult](Protocol):
    """Protocol for typed message handlers.

    Type Parameters:
        TMessage: The message type this handler processes.
        TResult: The result type returned by the handler.
    """

    async def handle(self, message: TMessage) -> TResult:
        """Handle a message and return result."""
        ...


class AsyncMessageHandler[TMessage, TResult](ABC):
    """Abstract async message handler.

    Type Parameters:
        TMessage: The message type this handler processes.
        TResult: The result type returned by the handler.
    """

    @abstractmethod
    async def handle(self, message: TMessage) -> TResult:
        """Handle a message and return result."""
        ...


# =============================================================================
# Subscription
# =============================================================================


@dataclass
class Subscription[TEvent]:
    """Type-safe event subscription.

    Type Parameters:
        TEvent: The event type this subscription handles.
    """

    event_type: type[TEvent]
    handler: Callable[[TEvent], Awaitable[None]]
    filter_fn: Callable[[TEvent], bool] | None = None

    async def handle(self, event: TEvent) -> None:
        """Handle event if it passes filter."""
        if self.filter_fn is None or self.filter_fn(event):
            await self.handler(event)


class FilteredSubscription[TEvent, TFilter]:
    """Subscription with typed filter predicate.

    Type Parameters:
        TEvent: The event type this subscription handles.
        TFilter: The filter configuration type.
    """

    def __init__(
        self,
        event_type: type[TEvent],
        handler: Callable[[TEvent], Awaitable[None]],
        filter_config: TFilter,
        predicate: Callable[[TEvent, TFilter], bool],
    ) -> None:
        self._event_type = event_type
        self._handler = handler
        self._filter_config = filter_config
        self._predicate = predicate

    async def handle(self, event: TEvent) -> None:
        """Handle event if it passes filter."""
        if self._predicate(event, self._filter_config):
            await self._handler(event)


# =============================================================================
# Message Broker
# =============================================================================


@runtime_checkable
class MessageBroker[TMessage](Protocol):
    """Protocol for message broker implementations.

    Type Parameters:
        TMessage: The message type this broker handles.
    """

    async def publish(self, topic: str, message: TMessage) -> None:
        """Publish message to topic."""
        ...

    async def subscribe(
        self,
        topic: str,
        handler: MessageHandler[TMessage, None],
    ) -> None:
        """Subscribe handler to topic."""
        ...

    async def unsubscribe(self, topic: str) -> None:
        """Unsubscribe from topic."""
        ...


class InMemoryBroker[TMessage]:
    """In-memory message broker for testing.

    Type Parameters:
        TMessage: The message type this broker handles.
    """

    def __init__(self) -> None:
        self._subscriptions: dict[str, list[MessageHandler[TMessage, None]]] = {}
        self._messages: list[tuple[str, TMessage]] = []

    async def publish(self, topic: str, message: TMessage) -> None:
        """Publish message to topic."""
        self._messages.append((topic, message))
        handlers = self._subscriptions.get(topic, [])
        await asyncio.gather(
            *[h.handle(message) for h in handlers],
            return_exceptions=True,
        )

    async def subscribe(
        self,
        topic: str,
        handler: MessageHandler[TMessage, None],
    ) -> None:
        """Subscribe handler to topic."""
        if topic not in self._subscriptions:
            self._subscriptions[topic] = []
        self._subscriptions[topic].append(handler)

    async def unsubscribe(self, topic: str) -> None:
        """Unsubscribe from topic."""
        self._subscriptions.pop(topic, None)

    def get_messages(self, topic: str | None = None) -> list[TMessage]:
        """Get published messages, optionally filtered by topic."""
        if topic is None:
            return [m for _, m in self._messages]
        return [m for t, m in self._messages if t == topic]


# =============================================================================
# Dead Letter Queue
# =============================================================================


@dataclass
class DeadLetter[TMessage]:
    """A message that failed processing.

    Type Parameters:
        TMessage: The original message type.
    """

    message: TMessage
    error: str
    retry_count: int
    first_failure: datetime
    last_failure: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class DeadLetterQueue[TMessage](Protocol):
    """Protocol for dead letter queue implementations.

    Type Parameters:
        TMessage: The message type this DLQ handles.
    """

    async def enqueue(self, dead_letter: DeadLetter[TMessage]) -> None:
        """Add message to dead letter queue."""
        ...

    async def dequeue(self) -> DeadLetter[TMessage] | None:
        """Remove and return oldest message from queue."""
        ...

    async def peek(self, count: int = 10) -> list[DeadLetter[TMessage]]:
        """View messages without removing them."""
        ...

    async def retry(self, message_id: str) -> bool:
        """Retry a dead letter message."""
        ...

    async def discard(self, message_id: str) -> bool:
        """Permanently discard a dead letter message."""
        ...


class InMemoryDLQ[TMessage]:
    """In-memory dead letter queue for testing.

    Type Parameters:
        TMessage: The message type this DLQ handles.
    """

    def __init__(self) -> None:
        self._queue: list[DeadLetter[TMessage]] = []

    async def enqueue(self, dead_letter: DeadLetter[TMessage]) -> None:
        """Add message to dead letter queue."""
        self._queue.append(dead_letter)

    async def dequeue(self) -> DeadLetter[TMessage] | None:
        """Remove and return oldest message from queue."""
        if self._queue:
            return self._queue.pop(0)
        return None

    async def peek(self, count: int = 10) -> list[DeadLetter[TMessage]]:
        """View messages without removing them."""
        return self._queue[:count]

    async def retry(self, message_id: str) -> bool:
        """Retry a dead letter message (stub)."""
        return False

    async def discard(self, message_id: str) -> bool:
        """Permanently discard a dead letter message (stub)."""
        return False

    @property
    def size(self) -> int:
        """Get queue size."""
        return len(self._queue)
