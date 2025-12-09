"""Outbox Pattern implementation for reliable messaging.

The Outbox Pattern ensures at-least-once delivery by storing messages
in the same transaction as domain changes.

Components:
- OutboxMessage: Message model with status, retries, idempotency
- OutboxRepository: In-memory implementation (use SQLModel for production)
- OutboxPublisher: Background publisher with exponential backoff
- IOutboxRepository: Protocol for custom repository implementations

**Feature: python-api-base-2025-validation**
**Validates: Requirements 33.1, 33.2, 33.3, 33.4, 33.5**
"""

from infrastructure.messaging.outbox.outbox_message import (
    OutboxMessage,
    OutboxMessageStatus,
    create_outbox_message,
)
from infrastructure.messaging.outbox.outbox_publisher import (
    IOutboxRepository,
    OutboxPublisher,
    OutboxPublisherContext,
)
from infrastructure.messaging.outbox.outbox_repository import OutboxRepository

__all__ = [
    # Message
    "OutboxMessage",
    "OutboxMessageStatus",
    "create_outbox_message",
    # Repository
    "IOutboxRepository",
    "OutboxRepository",
    # Publisher
    "OutboxPublisher",
    "OutboxPublisherContext",
]
