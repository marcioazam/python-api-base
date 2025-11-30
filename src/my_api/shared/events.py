"""Domain events system for decoupled communication.

Uses PEP 695 type parameter syntax (Python 3.12+) for cleaner generic definitions.
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4

from my_api.shared.utils.datetime import utc_now


@dataclass(frozen=True, slots=True)
class DomainEvent(ABC):
    """Base class for domain events.
    
    All domain events should inherit from this class and be immutable.
    """

    event_id: str = field(default_factory=lambda: str(uuid4()))
    occurred_at: datetime = field(default_factory=utc_now)

    @property
    @abstractmethod
    def event_type(self) -> str:
        """Return the event type identifier."""
        ...


@dataclass(frozen=True, slots=True)
class EntityCreatedEvent(DomainEvent):
    """Event emitted when an entity is created."""

    entity_type: str = ""
    entity_id: str = ""

    @property
    def event_type(self) -> str:
        return f"{self.entity_type}.created"


@dataclass(frozen=True, slots=True)
class EntityUpdatedEvent(DomainEvent):
    """Event emitted when an entity is updated."""

    entity_type: str = ""
    entity_id: str = ""
    changed_fields: tuple[str, ...] = ()

    @property
    def event_type(self) -> str:
        return f"{self.entity_type}.updated"


@dataclass(frozen=True, slots=True)
class EntityDeletedEvent(DomainEvent):
    """Event emitted when an entity is deleted."""

    entity_type: str = ""
    entity_id: str = ""
    soft_delete: bool = True

    @property
    def event_type(self) -> str:
        return f"{self.entity_type}.deleted"


type EventHandler = Callable[[DomainEvent], Any]


class EventBus:
    """Simple in-process event bus for domain events.
    
    Supports both sync and async handlers.
    """

    def __init__(self) -> None:
        """Initialize event bus."""
        self._handlers: dict[str, list[EventHandler]] = {}
        self._global_handlers: list[EventHandler] = []

    def subscribe(
        self,
        event_type: str | None = None,
        handler: EventHandler | None = None,
    ) -> Callable[[EventHandler], EventHandler]:
        """Subscribe a handler to an event type.
        
        Can be used as a decorator or called directly.
        
        Args:
            event_type: Event type to subscribe to. None for all events.
            handler: Handler function.
            
        Returns:
            Decorator function or the handler.
        """
        def decorator(fn: EventHandler) -> EventHandler:
            if event_type is None:
                self._global_handlers.append(fn)
            else:
                if event_type not in self._handlers:
                    self._handlers[event_type] = []
                self._handlers[event_type].append(fn)
            return fn

        if handler is not None:
            return decorator(handler)
        return decorator

    def unsubscribe(
        self,
        event_type: str | None,
        handler: EventHandler,
    ) -> None:
        """Unsubscribe a handler from an event type.
        
        Args:
            event_type: Event type to unsubscribe from.
            handler: Handler function to remove.
        """
        if event_type is None:
            if handler in self._global_handlers:
                self._global_handlers.remove(handler)
        elif event_type in self._handlers:
            if handler in self._handlers[event_type]:
                self._handlers[event_type].remove(handler)

    async def publish(self, event: DomainEvent) -> None:
        """Publish an event to all subscribed handlers.
        
        Args:
            event: Domain event to publish.
        """
        import asyncio
        import logging

        logger = logging.getLogger(__name__)
        handlers = self._global_handlers + self._handlers.get(event.event_type, [])

        for handler in handlers:
            try:
                result = handler(event)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error(
                    f"Event handler failed: {handler.__name__}",
                    extra={
                        "event_type": event.event_type,
                        "event_id": event.event_id,
                        "error": str(e),
                    },
                )

    def publish_sync(self, event: DomainEvent) -> None:
        """Publish an event synchronously (for sync handlers only).
        
        Args:
            event: Domain event to publish.
        """
        import logging

        logger = logging.getLogger(__name__)
        handlers = self._global_handlers + self._handlers.get(event.event_type, [])

        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(
                    f"Event handler failed: {handler.__name__}",
                    extra={
                        "event_type": event.event_type,
                        "event_id": event.event_id,
                        "error": str(e),
                    },
                )


# Global event bus instance
event_bus = EventBus()
