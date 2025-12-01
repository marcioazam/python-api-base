"""Webhook models with PEP 695 generics.

**Feature: enterprise-features-2025, Task 5.1: Create webhook models**
**Validates: Requirements 5.1, 5.8, 5.10**
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Protocol

from pydantic import SecretStr


class DeliveryStatus(Enum):
    """Webhook delivery status."""

    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"


class DeliveryError(Enum):
    """Webhook delivery error types."""

    TIMEOUT = "timeout"
    CONNECTION_ERROR = "connection_error"
    INVALID_RESPONSE = "invalid_response"
    MAX_RETRIES_EXCEEDED = "max_retries_exceeded"
    INVALID_URL = "invalid_url"
    SIGNATURE_ERROR = "signature_error"


@dataclass(frozen=True, slots=True)
class WebhookPayload[TEvent]:
    """Generic webhook payload with typed event data.

    Type Parameters:
        TEvent: The type of event data.
    """

    event_type: str
    event_id: str
    timestamp: datetime
    data: TEvent
    webhook_id: str = ""
    attempt: int = 1


@dataclass(frozen=True, slots=True)
class WebhookSubscription:
    """Webhook subscription configuration.

    Attributes:
        id: Unique subscription identifier.
        url: Target URL for webhook delivery.
        secret: Shared secret for HMAC signature.
        events: Set of event types to subscribe to.
        is_active: Whether subscription is active.
        created_at: When subscription was created.
        metadata: Additional subscription metadata.
    """

    id: str
    url: str
    secret: SecretStr
    events: frozenset[str]
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class DeliveryResult:
    """Result of webhook delivery attempt.

    Attributes:
        webhook_id: The webhook subscription ID.
        event_id: The event ID that was delivered.
        status_code: HTTP response status code.
        response_time_ms: Response time in milliseconds.
        delivered_at: When delivery completed.
        attempt: Delivery attempt number.
    """

    webhook_id: str
    event_id: str
    status_code: int
    response_time_ms: int
    delivered_at: datetime
    attempt: int = 1


@dataclass(frozen=True, slots=True)
class DeliveryFailure:
    """Details of a failed delivery attempt.

    Attributes:
        webhook_id: The webhook subscription ID.
        event_id: The event ID that failed.
        error: The error type.
        error_message: Detailed error message.
        attempt: Delivery attempt number.
        next_retry_at: When next retry will occur.
    """

    webhook_id: str
    event_id: str
    error: DeliveryError
    error_message: str
    attempt: int
    next_retry_at: datetime | None = None


class WebhookHandler[TEvent](Protocol):
    """Protocol for webhook event handlers.

    Type Parameters:
        TEvent: The type of event this handler processes.
    """

    async def handle(self, payload: WebhookPayload[TEvent]) -> None:
        """Handle a webhook payload."""
        ...
