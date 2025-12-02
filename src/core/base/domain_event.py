"""Compatibility alias for core.base.events.domain_event.

Use core.base.events.domain_event directly for new code.
"""

from core.base.events.domain_event import (
    DomainEvent,
    EntityCreatedEvent,
    EntityUpdatedEvent,
    EntityDeletedEvent,
    EventBus,
)

__all__ = [
    "DomainEvent",
    "EntityCreatedEvent",
    "EntityUpdatedEvent",
    "EntityDeletedEvent",
    "EventBus",
]
