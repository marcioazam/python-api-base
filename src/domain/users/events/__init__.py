"""User domain events.

Contains domain events for user aggregate.

**Feature: domain-restructuring-2025**
"""

from domain.users.events.events import (
    UserDeactivatedEvent,
    UserEmailChangedEvent,
    UserRegisteredEvent,
)

__all__ = [
    "UserDeactivatedEvent",
    "UserEmailChangedEvent",
    "UserRegisteredEvent",
]
