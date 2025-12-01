"""Users bounded context.

**Feature: architecture-restructuring-2025**
"""

from my_app.domain.users.aggregates import UserAggregate
from my_app.domain.users.value_objects import Email, PasswordHash, UserId, Username
from my_app.domain.users.events import (
    UserRegisteredEvent,
    UserDeactivatedEvent,
    UserEmailChangedEvent,
)
from my_app.domain.users.repositories import IUserRepository

__all__ = [
    "Email",
    "IUserRepository",
    "PasswordHash",
    "UserAggregate",
    "UserDeactivatedEvent",
    "UserEmailChangedEvent",
    "UserId",
    "UserRegisteredEvent",
    "Username",
]
