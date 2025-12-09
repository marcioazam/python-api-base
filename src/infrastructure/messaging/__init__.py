"""Messaging infrastructure.

Provides:
- Brokers: KafkaBroker, RabbitMQBroker
- Consumers: BaseConsumer
- Dead Letter Queue: DLQEntry, DLQHandler
- Outbox Pattern: OutboxMessage, OutboxPublisher, OutboxRepository, IOutboxRepository
"""

from infrastructure.messaging.brokers import KafkaBroker, RabbitMQBroker
from infrastructure.messaging.consumers import BaseConsumer
from infrastructure.messaging.dlq import DLQEntry, DLQHandler
from infrastructure.messaging.outbox import (
    IOutboxRepository,
    OutboxMessage,
    OutboxMessageStatus,
    OutboxPublisher,
    OutboxPublisherContext,
    OutboxRepository,
    create_outbox_message,
)

__all__ = [
    # Brokers
    "KafkaBroker",
    "RabbitMQBroker",
    # Consumers
    "BaseConsumer",
    # Dead Letter Queue
    "DLQEntry",
    "DLQHandler",
    # Outbox Pattern
    "IOutboxRepository",
    "OutboxMessage",
    "OutboxMessageStatus",
    "OutboxPublisher",
    "OutboxPublisherContext",
    "OutboxRepository",
    "create_outbox_message",
]
