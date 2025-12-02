"""RabbitMQ message broker implementation.

**Feature: architecture-restructuring-2025**
**Validates: Requirements 6.5**

WARNING: This module is NOT IMPLEMENTED and should not be used in production.
To implement RabbitMQ support, install aio-pika and complete the implementation.

Installation:
    pip install aio-pika

Implementation guide:
    https://aio-pika.readthedocs.io/
"""

import logging
import warnings
from dataclasses import dataclass
from typing import Any, Never

logger = logging.getLogger(__name__)

# Warn on import
warnings.warn(
    "RabbitMQBroker is not implemented. Do not use in production. "
    "Install aio-pika and complete implementation or use alternative broker.",
    category=UserWarning,
    stacklevel=2,
)


@dataclass
class RabbitMQConfig:
    """RabbitMQ broker configuration."""

    host: str = "localhost"
    port: int = 5672
    username: str | None = None
    password: str | None = None
    virtual_host: str = "/"


class RabbitMQBroker:
    """RabbitMQ message broker client stub.

    WARNING: This class is NOT IMPLEMENTED.
    All methods raise NotImplementedError.

    To implement:
        1. Install aio-pika: pip install aio-pika
        2. Initialize aio_pika.connect_robust() in connect()
        3. Create channel in connect()
        4. Implement publish() with channel.default_exchange.publish()
        5. Implement declare_queue() with channel.declare_queue()
        6. Implement consume() with queue.iterator()
    """

    def __init__(self, config: RabbitMQConfig | None = None) -> None:
        self._config = config or RabbitMQConfig()
        logger.warning(
            "RabbitMQBroker initialized but NOT IMPLEMENTED. "
            "All operations will raise NotImplementedError."
        )

    async def connect(self) -> Never:
        """Connect to RabbitMQ broker.

        Raises:
            NotImplementedError: Always. This method is not implemented.
        """
        raise NotImplementedError(
            "RabbitMQBroker.connect() not implemented. Install aio-pika and complete implementation."
        )

    async def disconnect(self) -> Never:
        """Disconnect from RabbitMQ broker.

        Raises:
            NotImplementedError: Always. This method is not implemented.
        """
        raise NotImplementedError("RabbitMQBroker.disconnect() not implemented.")

    async def publish(
        self, exchange: str, routing_key: str, message: dict[str, Any]
    ) -> Never:
        """Publish message to RabbitMQ exchange.

        Raises:
            NotImplementedError: Always. This method is not implemented.
        """
        raise NotImplementedError(
            f"RabbitMQBroker.publish() not implemented. Cannot publish to {exchange}/{routing_key}."
        )

    async def declare_queue(self, queue_name: str, durable: bool = True) -> Never:
        """Declare a queue.

        Raises:
            NotImplementedError: Always. This method is not implemented.
        """
        raise NotImplementedError(
            f"RabbitMQBroker.declare_queue() not implemented. Cannot declare {queue_name}."
        )

    async def consume(self, queue_name: str) -> Never:
        """Consume messages from queue.

        Raises:
            NotImplementedError: Always. This method is not implemented.
        """
        raise NotImplementedError(
            f"RabbitMQBroker.consume() not implemented. Cannot consume from {queue_name}."
        )
