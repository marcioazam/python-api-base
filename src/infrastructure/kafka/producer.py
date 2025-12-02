"""Generic Kafka producer with PEP 695 generics.

**Feature: observability-infrastructure**
**Requirement: R3 - Generic Kafka Producer/Consumer**
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any, Generic, Self, TypeVar

from infrastructure.kafka.config import KafkaConfig
from infrastructure.kafka.message import KafkaMessage, MessageMetadata

if TYPE_CHECKING:
    from aiokafka import AIOKafkaProducer

logger = logging.getLogger(__name__)

T = TypeVar("T")


class KafkaProducer(Generic[T]):
    """Generic async Kafka producer.

    Type-safe producer for sending messages to Kafka topics.

    **Feature: observability-infrastructure**
    **Requirement: R3.2 - Generic Producer**

    Example:
        >>> class UserEvent(BaseModel):
        ...     user_id: str
        ...     action: str
        ...
        >>> async with KafkaProducer[UserEvent](config, "user-events") as producer:
        ...     await producer.send(UserEvent(user_id="123", action="login"))
    """

    def __init__(
        self,
        config: KafkaConfig,
        topic: str,
        payload_class: type[T] | None = None,
    ) -> None:
        """Initialize producer.

        Args:
            config: Kafka configuration
            topic: Default topic to produce to
            payload_class: Message payload class (for type hints)
        """
        self._config = config
        self._topic = topic
        self._payload_class = payload_class
        self._producer: AIOKafkaProducer | None = None
        self._started = False

    @property
    def topic(self) -> str:
        """Get default topic."""
        return self._topic

    async def start(self) -> Self:
        """Start the producer.

        Returns:
            Self for chaining
        """
        if self._started:
            return self

        from aiokafka import AIOKafkaProducer

        producer_config = self._config.to_producer_config()

        self._producer = AIOKafkaProducer(**producer_config)
        await self._producer.start()
        self._started = True

        logger.info(
            "Kafka producer started",
            extra={"topic": self._topic, "servers": self._config.bootstrap_servers},
        )

        return self

    async def stop(self) -> None:
        """Stop the producer."""
        if self._producer and self._started:
            await self._producer.stop()
            self._producer = None
            self._started = False
            logger.info("Kafka producer stopped")

    async def __aenter__(self) -> Self:
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.stop()

    async def send(
        self,
        payload: T,
        key: str | None = None,
        headers: dict[str, str] | None = None,
        topic: str | None = None,
        partition: int | None = None,
    ) -> MessageMetadata:
        """Send a message to Kafka.

        Args:
            payload: Message payload
            key: Optional message key
            headers: Optional message headers
            topic: Topic to send to (defaults to configured topic)
            partition: Specific partition to send to

        Returns:
            Message metadata with offset info

        Raises:
            RuntimeError: If producer not started
        """
        if not self._producer or not self._started:
            raise RuntimeError("Producer not started")

        target_topic = topic or self._topic

        # Create message wrapper
        message = KafkaMessage[T](
            payload=payload,
            key=key,
            headers=headers or {},
        )

        # Send to Kafka
        result = await self._producer.send_and_wait(
            topic=target_topic,
            value=message.serialize(),
            key=message.serialize_key(),
            headers=message.serialize_headers() if message.headers else None,
            partition=partition,
        )

        metadata = MessageMetadata(
            topic=result.topic,
            partition=result.partition,
            offset=result.offset,
            timestamp=message.timestamp,
            key=key,
            headers=headers or {},
        )

        logger.debug(
            "Message sent",
            extra={
                "topic": metadata.topic,
                "partition": metadata.partition,
                "offset": metadata.offset,
            },
        )

        return metadata

    async def send_batch(
        self,
        payloads: list[T],
        key_func: callable | None = None,
        topic: str | None = None,
    ) -> list[MessageMetadata]:
        """Send multiple messages in a batch.

        Args:
            payloads: List of message payloads
            key_func: Function to extract key from payload
            topic: Topic to send to

        Returns:
            List of message metadata
        """
        if not self._producer or not self._started:
            raise RuntimeError("Producer not started")

        target_topic = topic or self._topic
        futures = []

        for payload in payloads:
            key = key_func(payload) if key_func else None
            message = KafkaMessage[T](payload=payload, key=key)

            future = await self._producer.send(
                topic=target_topic,
                value=message.serialize(),
                key=message.serialize_key(),
            )
            futures.append((future, message))

        # Wait for all sends to complete
        results = []
        for future, message in futures:
            result = await future
            metadata = MessageMetadata(
                topic=result.topic,
                partition=result.partition,
                offset=result.offset,
                timestamp=message.timestamp,
                key=message.key,
            )
            results.append(metadata)

        logger.info(
            f"Batch sent: {len(results)} messages",
            extra={"topic": target_topic},
        )

        return results

    async def flush(self) -> None:
        """Flush pending messages."""
        if self._producer:
            await self._producer.flush()
