"""Users bounded context.

Organized into subpackages by responsibility:
- aggregates/: User aggregate root
- events/: Domain events
- repositories/: Repository interface
- services/: Domain services
- value_objects/: Value objects

**Feature: domain-restructuring-2025**
"""

from domain.users.aggregates import UserAggregate
from domain.users.events import (
    UserDeactivatedEvent,
    UserEmailChangedEvent,
    UserRegisteredEvent,
)
from domain.users.repositories import IUserRepository
from domain.users.services import UserDomainService
from domain.users.value_objects import Email, PasswordHash, UserId, Username

__all__ = [
    "Email",
    "IUserRepository",
    "PasswordHash",
    "UserAggregate",
    "UserDeactivatedEvent",
    "UserDomainService",
    "UserEmailChangedEvent",
    "UserId",
    "UserRegisteredEvent",
    "Username",
]
