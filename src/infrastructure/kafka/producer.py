"""Generic Kafka producer with PEP 695 generics.

**Feature: observability-infrastructure**
**Requirement: R3 - Generic Kafka Producer/Consumer**
**Requirement: R3.1 - Transactional Producer with Exactly-Once Semantics**
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any, AsyncIterator, Generic, Self, TypeVar

from infrastructure.kafka.config import KafkaConfig
from infrastructure.kafka.message import KafkaMessage, MessageMetadata

if TYPE_CHECKING:
    from aiokafka import AIOKafkaProducer

logger = logging.getLogger(__name__)

T = TypeVar("T")


# =============================================================================
# Transactional Support (Exactly-Once Semantics)
# =============================================================================


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


# =============================================================================
# Transactional Producer (Exactly-Once Semantics)
# =============================================================================


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
            transactional_id: Unique ID for transactional producer (required for exactly-once)
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
        """Start the transactional producer.

        Initializes transactions for exactly-once semantics.
        """
        if self._started:
            return self

        from aiokafka import AIOKafkaProducer

        producer_config = self._config.to_producer_config()

        # Enable idempotence and transactions for exactly-once
        producer_config.update({
            "transactional_id": self._transactional_id,
            "enable_idempotence": True,
            "acks": "all",  # Required for transactions
            "max_in_flight_requests_per_connection": 5,  # Max for idempotence
        })

        self._producer = AIOKafkaProducer(**producer_config)
        await self._producer.start()

        # Initialize transactions
        await self._producer.init_transactions()

        self._started = True
        logger.info(
            "Transactional Kafka producer started",
            extra={
                "topic": self._topic,
                "transactional_id": self._transactional_id,
            },
        )

        return self

    async def stop(self) -> None:
        """Stop the transactional producer."""
        if self._producer and self._started:
            # Abort any pending transaction
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
    async def transaction(self) -> AsyncIterator["TransactionContext[T]"]:
        """Start a transaction context.

        **Requirement: R3.1 - Exactly-once semantics via transactions**

        All messages sent within the context are committed atomically.
        If an exception occurs, the transaction is aborted.

        Yields:
            TransactionContext for sending messages

        Example:
            >>> async with producer.transaction() as tx:
            ...     await tx.send(event1)
            ...     await tx.send(event2)
            ...     # Commit on exit
        """
        if not self._producer or not self._started:
            raise RuntimeError("Producer not started")

        if self._in_transaction:
            raise TransactionError(
                "Already in a transaction",
                self._transaction_state,
            )

        ctx = TransactionContext[T](self)

        try:
            await self._begin_transaction()
            yield ctx
            await self._commit_transaction()
        except Exception as e:
            await self._abort_transaction()
            raise TransactionError(
                f"Transaction failed: {e}",
                TransactionState.ABORTED,
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
                "No active transaction to commit",
                self._transaction_state,
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
        """Send a message within the current transaction.

        Args:
            payload: Message payload
            key: Optional message key
            headers: Optional headers
            topic: Target topic
            partition: Target partition

        Returns:
            Message metadata
        """
        if not self._producer or not self._started:
            raise RuntimeError("Producer not started")

        if not self._in_transaction:
            raise TransactionError(
                "Not in a transaction. Use transaction() context manager.",
                self._transaction_state,
            )

        target_topic = topic or self._topic

        message = KafkaMessage[T](
            payload=payload,
            key=key,
            headers=headers or {},
        )

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
    """Context for sending messages within a transaction.

    Provides a clean interface for transactional message sending.
    """

    def __init__(self, producer: TransactionalKafkaProducer[T]) -> None:
        """Initialize context.

        Args:
            producer: Parent transactional producer
        """
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
        """Send a message within the transaction.

        Args:
            payload: Message payload
            key: Optional message key
            headers: Optional headers
            topic: Target topic
            partition: Target partition

        Returns:
            Message metadata
        """
        metadata = await self._producer.send_in_transaction(
            payload=payload,
            key=key,
            headers=headers,
            topic=topic,
            partition=partition,
        )
        self._messages_sent.append(metadata)
        return metadata

    async def send_batch(
        self,
        payloads: list[T],
        key_func: callable | None = None,
        topic: str | None = None,
    ) -> list[MessageMetadata]:
        """Send multiple messages in the transaction.

        Args:
            payloads: List of payloads
            key_func: Function to extract key from payload
            topic: Target topic

        Returns:
            List of message metadata
        """
        results = []
        for payload in payloads:
            key = key_func(payload) if key_func else None
            metadata = await self.send(payload, key=key, topic=topic)
            results.append(metadata)
        return results
