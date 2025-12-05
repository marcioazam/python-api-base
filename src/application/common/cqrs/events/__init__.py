"""Domain Event Bus infrastructure.

Provides event handler protocol and typed event bus for domain events.

**Feature: python-api-base-2025-state-of-art**
"""

from application.common.cqrs.events.event_bus import (
    EventHandler,
    EventHandlerError,
    TypedEventBus,
)

__all__ = [
    "EventHandler",
    "EventHandlerError",
    "TypedEventBus",
]
