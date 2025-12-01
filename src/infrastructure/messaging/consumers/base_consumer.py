"""Base consumer pattern for message processing.

**Feature: architecture-restructuring-2025**
**Validates: Requirements 6.6**
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, TypeVar

logger = logging.getLogger(__name__)

TMessage = TypeVar("TMessage")


@dataclass
class ConsumerConfig:
    """Consumer configuration."""

    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    batch_size: int = 10
    prefetch_count: int = 10


class BaseConsumer(ABC, Generic[TMessage]):
    """Base class for message consumers."""

    def __init__(self, config: ConsumerConfig | None = None) -> None:
        self._config = config or ConsumerConfig()
        self._running = False

    @abstractmethod
    async def process_message(self, message: TMessage) -> bool:
        """Process a single message. Return True on success."""
        ...

    @abstractmethod
    async def fetch_messages(self, batch_size: int) -> list[TMessage]:
        """Fetch batch of messages from source."""
        ...

    @abstractmethod
    async def acknowledge(self, message: TMessage) -> None:
        """Acknowledge successful message processing."""
        ...

    @abstractmethod
    async def reject(self, message: TMessage, requeue: bool = False) -> None:
        """Reject message, optionally requeuing."""
        ...

    async def start(self) -> None:
        """Start consuming messages."""
        self._running = True
        logger.info(f"Starting consumer: {self.__class__.__name__}")

        while self._running:
            try:
                messages = await self.fetch_messages(self._config.batch_size)
                for message in messages:
                    await self._process_with_retry(message)
            except Exception as e:
                logger.error(f"Consumer error: {e}", exc_info=True)
                await asyncio.sleep(self._config.retry_delay_seconds)

    def stop(self) -> None:
        """Stop consuming messages."""
        self._running = False
        logger.info(f"Stopping consumer: {self.__class__.__name__}")

    async def _process_with_retry(self, message: TMessage) -> None:
        """Process message with retry logic."""
        retries = 0
        while retries <= self._config.max_retries:
            try:
                success = await self.process_message(message)
                if success:
                    await self.acknowledge(message)
                    return
                retries += 1
            except Exception as e:
                logger.warning(f"Processing failed (attempt {retries + 1}): {e}")
                retries += 1
                if retries <= self._config.max_retries:
                    await asyncio.sleep(self._config.retry_delay_seconds * retries)

        # Max retries exceeded - send to DLQ
        await self.reject(message, requeue=False)
        logger.error(f"Message sent to DLQ after {self._config.max_retries} retries")
