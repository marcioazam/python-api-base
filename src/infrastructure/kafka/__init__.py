"""Generic Kafka infrastructure.

Provides type-safe Kafka producer and consumer with PEP 695 generics.

**Feature: observability-infrastructure**
**Feature: kafka-workflow-integration**
**Requirement: R3 - Generic Kafka Producer/Consumer**
**Requirement: R3.1 - Transactional Producer with Exactly-Once Semantics**
"""

from infrastructure.kafka.config import KafkaConfig
from infrastructure.kafka.producer import (
    KafkaProducer,
    TransactionalKafkaProducer,
    TransactionContext,
    TransactionState,
    TransactionResult,
    TransactionError,
)
from infrastructure.kafka.consumer import KafkaConsumer
from infrastructure.kafka.message import KafkaMessage, MessageMetadata
from infrastructure.kafka.event_publisher import (
    DomainEvent,
    EventPublisher,
    KafkaEventPublisher,
    NoOpEventPublisher,
    ItemCreatedEvent,
    ItemUpdatedEvent,
    ItemDeletedEvent,
    create_event_publisher,
)

__all__ = [
    # Config
    "KafkaConfig",
    # Producer
    "KafkaProducer",
    "TransactionalKafkaProducer",
    "TransactionContext",
    "TransactionState",
    "TransactionResult",
    "TransactionError",
    # Consumer
    "KafkaConsumer",
    # Message
    "KafkaMessage",
    "MessageMetadata",
    # Event Publisher
    "DomainEvent",
    "EventPublisher",
    "KafkaEventPublisher",
    "NoOpEventPublisher",
    "ItemCreatedEvent",
    "ItemUpdatedEvent",
    "ItemDeletedEvent",
    "create_event_publisher",
]
