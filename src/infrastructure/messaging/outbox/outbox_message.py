"""Outbox message model for transactional messaging.

**Feature: python-api-base-2025-validation**
**Validates: Requirements 33.1, 33.2**
"""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class OutboxMessageStatus(StrEnum):
    """Status of outbox message."""

    PENDING = "pending"
    PROCESSING = "processing"
    PUBLISHED = "published"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"


class OutboxMessage(BaseModel):
    """Transactional outbox message.

    Stores domain events in the same transaction as domain changes,
    ensuring at-least-once delivery guarantees.

    Note:
        For production use, implement a persistent repository using SQLModel.
        The default OutboxRepository is in-memory and suitable only for testing.

    **Feature: python-api-base-2025-validation**
    **Validates: Requirements 33.1, 33.2**
    """

    id: UUID = Field(default_factory=uuid4, description="Unique message ID")
    aggregate_type: str = Field(..., description="Type of aggregate (e.g., 'User', 'Order')")
    aggregate_id: str = Field(..., description="ID of the aggregate")
    event_type: str = Field(..., description="Type of event (e.g., 'UserCreated')")
    payload: dict[str, Any] = Field(default_factory=dict, description="Event payload")
    correlation_id: str | None = Field(
        default=None, description="Correlation ID for distributed tracing"
    )
    idempotency_key: str | None = Field(
        default=None, description="Key for deduplication"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata (tenant_id, user_id, etc.)"
    )
    status: OutboxMessageStatus = Field(
        default=OutboxMessageStatus.PENDING, description="Message status"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Creation timestamp"
    )
    processed_at: datetime | None = Field(
        default=None, description="When message was published"
    )
    retry_count: int = Field(default=0, description="Number of publish attempts")
    max_retries: int = Field(default=5, description="Maximum retry attempts")
    last_error: str | None = Field(default=None, description="Last error message")
    next_retry_at: datetime | None = Field(
        default=None, description="When to retry next"
    )

    model_config = {"frozen": False}

    def mark_processing(self) -> None:
        """Mark message as being processed."""
        self.status = OutboxMessageStatus.PROCESSING

    def mark_published(self) -> None:
        """Mark message as successfully published."""
        self.status = OutboxMessageStatus.PUBLISHED
        self.processed_at = datetime.now(UTC)
        self.last_error = None

    def mark_failed(self, error: str, next_retry: datetime | None = None) -> None:
        """Mark message as failed.

        Args:
            error: Error message.
            next_retry: When to retry next.
        """
        self.retry_count += 1
        self.last_error = error
        self.next_retry_at = next_retry

        if self.retry_count >= self.max_retries:
            self.status = OutboxMessageStatus.DEAD_LETTER
        else:
            self.status = OutboxMessageStatus.FAILED

    def mark_dead_letter(self, error: str) -> None:
        """Move message to dead letter queue.

        Args:
            error: Final error message.
        """
        self.status = OutboxMessageStatus.DEAD_LETTER
        self.last_error = error

    @property
    def can_retry(self) -> bool:
        """Check if message can be retried."""
        return (
            self.status in (OutboxMessageStatus.PENDING, OutboxMessageStatus.FAILED)
            and self.retry_count < self.max_retries
        )

    @property
    def is_ready_for_retry(self) -> bool:
        """Check if message is ready for retry based on next_retry_at."""
        if not self.can_retry:
            return False
        if self.next_retry_at is None:
            return True
        return datetime.now(UTC) >= self.next_retry_at

    def to_event_dict(self) -> dict[str, Any]:
        """Convert to event dictionary for publishing.

        Returns:
            Event dictionary with metadata.
        """
        return {
            "id": str(self.id),
            "type": self.event_type,
            "aggregate_type": self.aggregate_type,
            "aggregate_id": self.aggregate_id,
            "payload": self.payload,
            "timestamp": self.created_at.isoformat(),
            "idempotency_key": self.idempotency_key,
            "correlation_id": self.correlation_id,
            "metadata": self.metadata,
        }


def create_outbox_message(
    aggregate_type: str,
    aggregate_id: str,
    event_type: str,
    payload: dict[str, Any],
    idempotency_key: str | None = None,
    correlation_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> OutboxMessage:
    """Factory function to create outbox message.

    Args:
        aggregate_type: Type of aggregate.
        aggregate_id: ID of aggregate.
        event_type: Type of event.
        payload: Event payload.
        idempotency_key: Optional idempotency key.
        correlation_id: Optional correlation ID for tracing.
        metadata: Optional additional metadata.

    Returns:
        New OutboxMessage instance.
    """
    return OutboxMessage(
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        event_type=event_type,
        payload=payload,
        idempotency_key=idempotency_key or f"{aggregate_type}:{aggregate_id}:{event_type}:{uuid4()}",
        correlation_id=correlation_id,
        metadata=metadata or {},
    )
