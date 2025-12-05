"""Domain events for the Users bounded context.

**Feature: architecture-restructuring-2025**
**Validates: Requirements 2.6**
"""

from dataclasses import dataclass
from datetime import UTC, datetime

from core.base.events.domain_event import DomainEvent

try:
    from core.shared.utils.time import utc_now
except ImportError:

    def utc_now() -> datetime:
        return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class UserRegisteredEvent(DomainEvent):
    """Event emitted when a new user registers."""

    user_id: str = ""
    email: str = ""

    @property
    def event_type(self) -> str:
        return "user.registered"


@dataclass(frozen=True, slots=True)
class UserDeactivatedEvent(DomainEvent):
    """Event emitted when a user is deactivated."""

    user_id: str = ""
    reason: str = ""

    @property
    def event_type(self) -> str:
        return "user.deactivated"


@dataclass(frozen=True, slots=True)
class UserEmailChangedEvent(DomainEvent):
    """Event emitted when a user changes their email."""

    user_id: str = ""
    old_email: str = ""
    new_email: str = ""

    @property
    def event_type(self) -> str:
        return "user.email_changed"


@dataclass(frozen=True, slots=True)
class UserPasswordChangedEvent(DomainEvent):
    """Event emitted when a user changes their password."""

    user_id: str = ""

    @property
    def event_type(self) -> str:
        return "user.password_changed"


@dataclass(frozen=True, slots=True)
class UserEmailVerifiedEvent(DomainEvent):
    """Event emitted when a user verifies their email."""

    user_id: str = ""
    email: str = ""

    @property
    def event_type(self) -> str:
        return "user.email_verified"


@dataclass(frozen=True, slots=True)
class UserLoggedInEvent(DomainEvent):
    """Event emitted when a user logs in."""

    user_id: str = ""
    ip_address: str = ""
    user_agent: str = ""

    @property
    def event_type(self) -> str:
        return "user.logged_in"


@dataclass(frozen=True, slots=True)
class UserReactivatedEvent(DomainEvent):
    """Event emitted when a user is reactivated."""

    user_id: str = ""

    @property
    def event_type(self) -> str:
        return "user.reactivated"


@dataclass(frozen=True, slots=True)
class UserProfileUpdatedEvent(DomainEvent):
    """Event emitted when a user updates their profile."""

    user_id: str = ""
    changed_fields: tuple[str, ...] = ()

    @property
    def event_type(self) -> str:
        return "user.profile_updated"
