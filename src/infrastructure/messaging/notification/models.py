"""Notification models with PEP 695 generics.

**Feature: enterprise-features-2025, Task 8.1**
**Validates: Requirements 8.8, 8.9, 8.10**
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Protocol

from core.base.result import Result


class NotificationStatus(Enum):
    """Notification delivery status."""

    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"
    SKIPPED = "skipped"


class NotificationError(Enum):
    """Notification error types."""

    INVALID_RECIPIENT = "invalid_recipient"
    TEMPLATE_ERROR = "template_error"
    CHANNEL_ERROR = "channel_error"
    RATE_LIMITED = "rate_limited"
    OPT_OUT = "opt_out"


@dataclass(frozen=True, slots=True)
class Notification:
    """A notification to be sent."""

    id: str
    recipient_id: str
    channel: str
    template_id: str
    context: dict[str, Any]
    status: NotificationStatus = NotificationStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    sent_at: datetime | None = None
    error: NotificationError | None = None


@dataclass(frozen=True, slots=True)
class UserPreferences:
    """User notification preferences."""

    user_id: str
    email_enabled: bool = True
    sms_enabled: bool = True
    push_enabled: bool = True
    opted_out_channels: frozenset[str] = frozenset()


class NotificationChannel[TPayload](Protocol):
    """Protocol for notification channels."""

    async def send(
        self, recipient: str, payload: TPayload
    ) -> Result[NotificationStatus, NotificationError]:
        """Send a notification."""
        ...

    async def send_batch(
        self, messages: list[tuple[str, TPayload]]
    ) -> list[Result[NotificationStatus, NotificationError]]:
        """Send batch of notifications."""
        ...


class Template[TContext](Protocol):
    """Protocol for notification templates."""

    def render(self, context: TContext, locale: str = "en") -> str:
        """Render template with context."""
        ...
