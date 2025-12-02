"""Kafka message broker implementation.

**Feature: architecture-restructuring-2025**
**Validates: Requirements 6.5**

WARNING: This module is NOT IMPLEMENTED and should not be used in production.
To implement Kafka support, install aiokafka and complete the implementation.

Installation:
    pip install aiokafka

Implementation guide:
    https://aiokafka.readthedocs.io/
"""

import logging
import warnings
from dataclasses import dataclass
from typing import Any, Never

logger = logging.getLogger(__name__)

# Warn on import
warnings.warn(
    "KafkaBroker is not implemented. Do not use in production. "
    "Install aiokafka and complete implementation or use alternative broker.",
    category=UserWarning,
    stacklevel=2,
)


@dataclass
class KafkaConfig:
    """Kafka broker configuration."""

    bootstrap_servers: str = "localhost:9092"
    client_id: str = "my_app"
    group_id: str = "my_app_group"
    auto_offset_reset: str = "earliest"
    enable_auto_commit: bool = True


class KafkaBroker:
    """Kafka message broker client stub.

    WARNING: This class is NOT IMPLEMENTED.
    All methods raise NotImplementedError.

    To implement:
        1. Install aiokafka: pip install aiokafka
        2. Initialize AIOKafkaProducer in connect()
        3. Initialize AIOKafkaConsumer in connect()
        4. Implement publish() with producer.send_and_wait()
        5. Implement subscribe() with consumer.subscribe()
        6. Implement consume() with consumer.getone()
    """

    def __init__(self, config: KafkaConfig | None = None) -> None:
        self._config = config or KafkaConfig()
        logger.warning(
            "KafkaBroker initialized but NOT IMPLEMENTED. "
            "All operations will raise NotImplementedError."
        )

    async def connect(self) -> Never:
        """Connect to Kafka broker.

        Raises:
            NotImplementedError: Always. This method is not implemented.
        """
        raise NotImplementedError(
            "KafkaBroker.connect() not implemented. Install aiokafka and complete implementation."
        )

    async def disconnect(self) -> Never:
        """Disconnect from Kafka broker.

        Raises:
            NotImplementedError: Always. This method is not implemented.
        """
        raise NotImplementedError("KafkaBroker.disconnect() not implemented.")

    async def publish(
        self, topic: str, message: dict[str, Any], key: str | None = None
    ) -> Never:
        """Publish message to Kafka topic.

        Raises:
            NotImplementedError: Always. This method is not implemented.
        """
        raise NotImplementedError(
            f"KafkaBroker.publish() not implemented. Cannot publish to {topic}."
        )

    async def subscribe(self, topics: list[str]) -> Never:
        """Subscribe to Kafka topics.

        Raises:
            NotImplementedError: Always. This method is not implemented.
        """
        raise NotImplementedError(
            f"KafkaBroker.subscribe() not implemented. Cannot subscribe to {topics}."
        )

    async def consume(self) -> Never:
        """Consume next message from subscribed topics.

        Raises:
            NotImplementedError: Always. This method is not implemented.
        """
        raise NotImplementedError("KafkaBroker.consume() not implemented.")
