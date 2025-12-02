"""Generic Kafka consumer with PEP 695 generics.

**Feature: observability-infrastructure**
**Requirement: R3 - Generic Kafka Producer/Consumer**
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator, Callable, Awaitable
from datetime import datetime, UTC
from typing import TYPE_CHECKING, Any, Generic, Self, TypeVar

from infrastructure.kafka.config import KafkaConfig
from infrastructure.kafka.message import KafkaMessage, MessageMetadata

if TYPE_CHECKING:
    from aiokafka import AIOKafkaConsumer, ConsumerRecord

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Message handler type
MessageHandler = Callable[[KafkaMessage[T]], Awaitable[None]]


class KafkaConsumer(Generic[T]):
    """Generic async Kafka consumer.

    Type-safe consumer for receiving messages from Kafka topics.

    **Feature: observability-infrastructure**
    **Requirement: R3.3 - Generic Consumer**

    Example:
        >>> class UserEvent(BaseModel):
        ...     user_id: str
        ...     action: str
        ...
        >>> async with KafkaConsumer[UserEvent](config, "user-events", UserEvent) as consumer:
        ...     async for message in consumer:
        ...         print(f"User {message.payload.user_id} did {message.payload.action}")
    """

    def __init__(
        self,
        config: KafkaConfig,
        topics: str | list[str],
        payload_class: type[T],
    ) -> None:
        """Initialize consumer.

        Args:
            config: Kafka configuration
            topics: Topic(s) to consume from
            payload_class: Message payload class for deserialization
        """
        self._config = config
        self._topics = [topics] if isinstance(topics, str) else topics
        self._payload_class = payload_class
        self._consumer: AIOKafkaConsumer | None = None
        self._started = False
        self._handlers: list[MessageHandler[T]] = []

    @property
    def topics(self) -> list[str]:
        """Get subscribed topics."""
        return self._topics

    async def start(self) -> Self:
        """Start the consumer.

        Returns:
            Self for chaining
        """
        if self._started:
            return self

        from aiokafka import AIOKafkaConsumer

        consumer_config = self._config.to_consumer_config()

        self._consumer = AIOKafkaConsumer(
            *self._topics,
            **consumer_config,
        )
        await self._consumer.start()
        self._started = True

        logger.info(
            "Kafka consumer started",
            extra={"topics": self._topics, "group_id": self._config.group_id},
        )

        return self

    async def stop(self) -> None:
        """Stop the consumer."""
        if self._consumer and self._started:
            await self._consumer.stop()
            self._consumer = None
            self._started = False
            logger.info("Kafka consumer stopped")

    async def __aenter__(self) -> Self:
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.stop()

    def _deserialize_record(self, record: ConsumerRecord) -> KafkaMessage[T]:
        """Deserialize a Kafka record to message.

        Args:
            record: Kafka consumer record

        Returns:
            Deserialized message with metadata
        """
        message = KafkaMessage.deserialize(
            payload_class=self._payload_class,
            value=record.value,
            key=record.key,
            headers=record.headers,
        )

        metadata = MessageMetadata(
            topic=record.topic,
            partition=record.partition,
            offset=record.offset,
            timestamp=datetime.fromtimestamp(record.timestamp / 1000, UTC) if record.timestamp else None,
            key=message.key,
            headers=message.headers,
        )

        return message.with_metadata(metadata)

    async def __aiter__(self) -> AsyncIterator[KafkaMessage[T]]:
        """Async iterator over messages.

        Yields:
            Deserialized messages
        """
        if not self._consumer or not self._started:
            raise RuntimeError("Consumer not started")

        async for record in self._consumer:
            try:
                message = self._deserialize_record(record)
                yield message
            except Exception as e:
                logger.error(
                    f"Failed to deserialize message: {e}",
                    extra={
                        "topic": record.topic,
                        "partition": record.partition,
                        "offset": record.offset,
                    },
                )

    async def consume_one(self, timeout_ms: int = 5000) -> KafkaMessage[T] | None:
        """Consume a single message.

        Args:
            timeout_ms: Timeout in milliseconds

        Returns:
            Message or None if timeout
        """
        if not self._consumer or not self._started:
            raise RuntimeError("Consumer not started")

        records = await self._consumer.getmany(timeout_ms=timeout_ms, max_records=1)

        for topic_partition, partition_records in records.items():
            if partition_records:
                return self._deserialize_record(partition_records[0])

        return None

    async def consume_batch(
        self,
        max_records: int = 100,
        timeout_ms: int = 5000,
    ) -> list[KafkaMessage[T]]:
        """Consume a batch of messages.

        Args:
            max_records: Maximum records to consume
            timeout_ms: Timeout in milliseconds

        Returns:
            List of messages
        """
        if not self._consumer or not self._started:
            raise RuntimeError("Consumer not started")

        records = await self._consumer.getmany(
            timeout_ms=timeout_ms,
            max_records=max_records,
        )

        messages = []
        for topic_partition, partition_records in records.items():
            for record in partition_records:
                try:
                    message = self._deserialize_record(record)
                    messages.append(message)
                except Exception as e:
                    logger.error(f"Failed to deserialize message: {e}")

        return messages

    def add_handler(self, handler: MessageHandler[T]) -> None:
        """Add a message handler.

        Args:
            handler: Async function to handle messages
        """
        self._handlers.append(handler)

    async def run(self, stop_event: asyncio.Event | None = None) -> None:
        """Run the consumer loop with registered handlers.

        Args:
            stop_event: Optional event to signal stop
        """
        if not self._handlers:
            raise RuntimeError("No handlers registered")

        logger.info("Starting consumer loop")

        async for message in self:
            if stop_event and stop_event.is_set():
                break

            for handler in self._handlers:
                try:
                    await handler(message)
                except Exception as e:
                    logger.error(
                        f"Handler error: {e}",
                        extra={
                            "topic": message.metadata.topic if message.metadata else None,
                            "offset": message.metadata.offset if message.metadata else None,
                        },
                    )

    async def commit(self) -> None:
        """Manually commit offsets."""
        if self._consumer:
            await self._consumer.commit()

    async def seek_to_beginning(self, *partitions: Any) -> None:
        """Seek to beginning of partitions.

        Args:
            *partitions: TopicPartition objects (or all if empty)
        """
        if self._consumer:
            await self._consumer.seek_to_beginning(*partitions)

    async def seek_to_end(self, *partitions: Any) -> None:
        """Seek to end of partitions.

        Args:
            *partitions: TopicPartition objects (or all if empty)
        """
        if self._consumer:
            await self._consumer.seek_to_end(*partitions)

    def assignment(self) -> set[Any]:
        """Get current partition assignment.

        Returns:
            Set of TopicPartition objects
        """
        if self._consumer:
            return self._consumer.assignment()
        return set()
