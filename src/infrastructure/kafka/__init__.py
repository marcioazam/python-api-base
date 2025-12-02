"""Generic Kafka infrastructure.

Provides type-safe Kafka producer and consumer with PEP 695 generics.

**Feature: observability-infrastructure**
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
]
