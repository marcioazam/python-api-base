"""Kafka transactional producer with exactly-once semantics.

**Feature: observability-infrastructure**
**Requirement: R3.1 - Transactional Producer with Exactly-Once Semantics**
**Refactored: 2025 - Extracted from producer.py for SRP compliance**
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any, Generic, Self, TypeVar

from infrastructure.kafka.config import KafkaConfig
from infrastructure.kafka.message import KafkaMessage, MessageMetadata

if TYPE_CHECKING:
    from aiokafka import AIOKafkaProducer

logger = logging.getLogger(__name__)

T = TypeVar("T")


class TransactionState(Enum):
    """Transaction state machine."""

    IDLE = "idle"
    STARTED = "started"
    COMMITTING = "committing"
    COMMITTED = "committed"
    ABORTING = "aborting"
    ABORTED = "aborted"
    ERROR = "error"


@dataclass
class TransactionResult:
    """Result of a transactional operation.

    **Requirement: R3.1 - Transactional result tracking**
    """

    transaction_id: str
    state: TransactionState
    messages_sent: int
    committed: bool
    error: str | None = None


class TransactionError(Exception):
    """Transaction-related error."""

    def __init__(self, message: str, state: TransactionState) -> None:
        super().__init__(message)
        self.state = state


class TransactionalKafkaProducer(Generic[T]):
    """Transactional Kafka producer with exactly-once semantics.

    **Requirement: R3.1 - Transactional Producer with Exactly-Once Semantics**

    Provides atomic message delivery guarantees using Kafka transactions.
    Messages are either all delivered or none are delivered.

    Example:
        >>> async with TransactionalKafkaProducer[OrderEvent](config, "orders") as producer:
        ...     async with producer.transaction() as tx:
        ...         await tx.send(OrderEvent(order_id="1", status="created"))
        ...         await tx.send(OrderEvent(order_id="1", status="paid"))
        ...     # Both messages committed atomically
    """

    def __init__(
        self,
        config: KafkaConfig,
        topic: str,
        transactional_id: str | None = None,
        payload_class: type[T] | None = None,
    ) -> None:
        """Initialize transactional producer.

        Args:
            config: Kafka configuration
            topic: Default topic
            transactional_id: Unique ID for transactional producer
            payload_class: Message payload class
        """
        self._config = config
        self._topic = topic
        self._transactional_id = transactional_id or f"txn-{config.client_id}"
        self._payload_class = payload_class
        self._producer: AIOKafkaProducer | None = None
        self._started = False
        self._in_transaction = False
        self._transaction_state = TransactionState.IDLE
        self._messages_in_transaction = 0

    @property
    def transactional_id(self) -> str:
        """Get transactional ID."""
        return self._transactional_id

    @property
    def in_transaction(self) -> bool:
        """Check if currently in a transaction."""
        return self._in_transaction

    @property
    def transaction_state(self) -> TransactionState:
        """Get current transaction state."""
        return self._transaction_state

    async def start(self) -> Self:
        """Start the transactional producer."""
        if self._started:
            return self

        from aiokafka import AIOKafkaProducer

        producer_config = self._config.to_producer_config()
        producer_config.update({
            "transactional_id": self._transactional_id,
            "enable_idempotence": True,
            "acks": "all",
            "max_in_flight_requests_per_connection": 5,
        })

        self._producer = AIOKafkaProducer(**producer_config)
        await self._producer.start()
        await self._producer.init_transactions()

        self._started = True
        logger.info(
            "Transactional Kafka producer started",
            extra={"topic": self._topic, "transactional_id": self._transactional_id},
        )
        return self

    async def stop(self) -> None:
        """Stop the transactional producer."""
        if self._producer and self._started:
            if self._in_transaction:
                await self._abort_transaction()
            await self._producer.stop()
            self._producer = None
            self._started = False
            logger.info("Transactional Kafka producer stopped")

    async def __aenter__(self) -> Self:
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.stop()

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[TransactionContext[T]]:
        """Start a transaction context.

        All messages sent within the context are committed atomically.
        If an exception occurs, the transaction is aborted.

        Yields:
            TransactionContext for sending messages
        """
        if not self._producer or not self._started:
            raise RuntimeError("Producer not started")

        if self._in_transaction:
            raise TransactionError("Already in a transaction", self._transaction_state)

        ctx = TransactionContext[T](self)

        try:
            await self._begin_transaction()
            yield ctx
            await self._commit_transaction()
        except Exception as e:
            await self._abort_transaction()
            raise TransactionError(
                f"Transaction failed: {e}", TransactionState.ABORTED
            ) from e

    async def _begin_transaction(self) -> None:
        """Begin a new transaction."""
        if not self._producer:
            raise RuntimeError("Producer not started")

        await self._producer.begin_transaction()
        self._in_transaction = True
        self._transaction_state = TransactionState.STARTED
        self._messages_in_transaction = 0
        logger.debug("Transaction started", extra={"txn_id": self._transactional_id})

    async def _commit_transaction(self) -> None:
        """Commit the current transaction."""
        if not self._producer or not self._in_transaction:
            raise TransactionError(
                "No active transaction to commit", self._transaction_state
            )

        self._transaction_state = TransactionState.COMMITTING
        try:
            await self._producer.commit_transaction()
            self._transaction_state = TransactionState.COMMITTED
            logger.info(
                "Transaction committed",
                extra={
                    "txn_id": self._transactional_id,
                    "messages": self._messages_in_transaction,
                },
            )
        finally:
            self._in_transaction = False
            self._messages_in_transaction = 0

    async def _abort_transaction(self) -> None:
        """Abort the current transaction."""
        if not self._producer:
            return

        self._transaction_state = TransactionState.ABORTING
        try:
            await self._producer.abort_transaction()
            self._transaction_state = TransactionState.ABORTED
            logger.warning(
                "Transaction aborted",
                extra={
                    "txn_id": self._transactional_id,
                    "messages_lost": self._messages_in_transaction,
                },
            )
        finally:
            self._in_transaction = False
            self._messages_in_transaction = 0

    async def send_in_transaction(
        self,
        payload: T,
        key: str | None = None,
        headers: dict[str, str] | None = None,
        topic: str | None = None,
        partition: int | None = None,
    ) -> MessageMetadata:
        """Send a message within the current transaction."""
        if not self._producer or not self._started:
            raise RuntimeError("Producer not started")

        if not self._in_transaction:
            raise TransactionError(
                "Not in a transaction. Use transaction() context manager.",
                self._transaction_state,
            )

        target_topic = topic or self._topic
        message = KafkaMessage[T](payload=payload, key=key, headers=headers or {})

        result = await self._producer.send_and_wait(
            topic=target_topic,
            value=message.serialize(),
            key=message.serialize_key(),
            headers=message.serialize_headers() if message.headers else None,
            partition=partition,
        )

        self._messages_in_transaction += 1

        metadata = MessageMetadata(
            topic=result.topic,
            partition=result.partition,
            offset=result.offset,
            timestamp=message.timestamp,
            key=key,
            headers=headers or {},
        )

        logger.debug(
            "Message sent in transaction",
            extra={
                "txn_id": self._transactional_id,
                "topic": metadata.topic,
                "offset": metadata.offset,
            },
        )
        return metadata


class TransactionContext(Generic[T]):
    """Context for sending messages within a transaction."""

    def __init__(self, producer: TransactionalKafkaProducer[T]) -> None:
        """Initialize context."""
        self._producer = producer
        self._messages_sent: list[MessageMetadata] = []

    @property
    def messages_sent(self) -> list[MessageMetadata]:
        """Get list of messages sent in this transaction."""
        return self._messages_sent.copy()

    @property
    def message_count(self) -> int:
        """Get count of messages sent."""
        return len(self._messages_sent)

    async def send(
        self,
        payload: T,
        key: str | None = None,
        headers: dict[str, str] | None = None,
        topic: str | None = None,
        partition: int | None = None,
    ) -> MessageMetadata:
        """Send a message within the transaction."""
        metadata = await self._producer.send_in_transaction(
            payload=payload, key=key, headers=headers, topic=topic, partition=partition
        )
        self._messages_sent.append(metadata)
        return metadata

    async def send_batch(
        self,
        payloads: list[T],
        key_func: callable | None = None,
        topic: str | None = None,
    ) -> list[MessageMetadata]:
        """Send multiple messages in the transaction."""
        results = []
        for payload in payloads:
            key = key_func(payload) if key_func else None
            metadata = await self.send(payload, key=key, topic=topic)
            results.append(metadata)
        return results
