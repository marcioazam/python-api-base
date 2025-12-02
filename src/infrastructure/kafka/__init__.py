"""Generic Kafka infrastructure.

Provides type-safe Kafka producer and consumer with PEP 695 generics.

**Feature: observability-infrastructure**
**Requirement: R3 - Generic Kafka Producer/Consumer**
"""

from infrastructure.kafka.config import KafkaConfig
from infrastructure.kafka.producer import KafkaProducer
from infrastructure.kafka.consumer import KafkaConsumer
from infrastructure.kafka.message import KafkaMessage, MessageMetadata

__all__ = [
    "KafkaConfig",
    "KafkaProducer",
    "KafkaConsumer",
    "KafkaMessage",
    "MessageMetadata",
]
