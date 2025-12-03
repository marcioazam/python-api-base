"""Domain Event Publisher for Kafka.

Provides abstraction for publishing domain events to Kafka topics.

**Feature: kafka-workflow-integration**
**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

logger = logging.getLogger(__name__)


# =============================================================================
# Domain Event Base
# =============================================================================


@dataclass
class DomainEvent(Generic[T]):
    """Base domain event with typed payload.

    Type Parameters:
        T: The payload type (must be Pydantic BaseModel).
    """

    event_type: str
    entity_type: str
    entity_id: str
    payload: T
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    correlation_id: str | None = None


# =============================================================================
# Item Domain Events
# =============================================================================


class ItemCreatedEvent(BaseModel):
    """Event published when ItemExample is created.

    **Validates: Requirements 3.1**
    """

    id: str
    name: str
    sku: str
    quantity: int
    created_by: str


class ItemUpdatedEvent(BaseModel):
    """Event published when ItemExample is updated.

    **Validates: Requirements 3.2**
    """

    id: str
    changes: dict[str, Any]
    updated_by: str


class ItemDeletedEvent(BaseModel):
    """Event published when ItemExample is deleted.

    **Validates: Requirements 3.3**
    """

    id: str
    deleted_by: str


# =============================================================================
# Event Publisher Interface
# =============================================================================


class EventPublisher(ABC):
    """Abstract event publisher interface.

    Implementations can publish to Kafka, RabbitMQ, or be no-op for testing.
    """

    @abstractmethod
    async def publish(self, event: DomainEvent[Any], topic: str) -> None:
        """Publish domain event to specified topic.

        Args:
            event: Domain event to publish
            topic: Target topic name
        """
        ...


class KafkaEventPublisher(EventPublisher):
    """Kafka implementation of event publisher.

    Publishes domain events to Kafka topics using KafkaProducer.

    **Validates: Requirements 3.1, 3.2, 3.3, 3.5**
    """

    def __init__(self, producer: Any | None) -> None:
        """Initialize with Kafka producer.

        Args:
            producer: KafkaProducer instance or None if Kafka disabled
        """
        self._producer = producer

    async def publish(self, event: DomainEvent[Any], topic: str) -> None:
        """Publish domain event to Kafka topic.

        If producer is None (Kafka disabled), silently skips.
        If publishing fails, logs error but does not raise.

        **Validates: Requirements 3.4, 3.5**
        """
        if self._producer is None:
            logger.debug(f"Kafka disabled, skipping event: {event.event_type}")
            return

        try:
            await self._producer.send(
                payload=event.payload,
                key=event.entity_id,
                headers={
                    "event_type": event.event_type,
                    "entity_type": event.entity_type,
                    "timestamp": event.timestamp.isoformat(),
                    "correlation_id": event.correlation_id or "",
                },
                topic=topic,
            )
            logger.info(
                f"Event published: {event.event_type}",
                extra={
                    "topic": topic,
                    "entity_id": event.entity_id,
                    "event_type": event.event_type,
                },
            )
        except Exception as e:
            # Fire-and-forget: log error but don't fail main operation
            logger.error(
                f"Failed to publish event: {e}",
                extra={
                    "event_type": event.event_type,
                    "entity_id": event.entity_id,
                    "error": str(e),
                },
            )


class NoOpEventPublisher(EventPublisher):
    """No-op event publisher for when Kafka is disabled.

    **Validates: Requirements 3.4**
    """

    async def publish(self, event: DomainEvent[Any], topic: str) -> None:
        """Do nothing - Kafka is disabled."""
        pass


# =============================================================================
# Factory Function
# =============================================================================


def create_event_publisher(kafka_producer: Any | None) -> EventPublisher:
    """Create appropriate event publisher based on Kafka availability.

    Args:
        kafka_producer: KafkaProducer instance or None

    Returns:
        KafkaEventPublisher if producer available, NoOpEventPublisher otherwise
    """
    if kafka_producer is not None:
        return KafkaEventPublisher(kafka_producer)
    return NoOpEventPublisher()
