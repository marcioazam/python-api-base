"""Retry Queue Pattern with dead letter queue handling."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, UTC
from enum import Enum
from typing import Protocol, Any
from collections.abc import Callable, Awaitable
import asyncio


class MessageStatus(Enum):
    """Message processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"


@dataclass
class RetryConfig:
    """Retry configuration."""
    max_retries: int = 3
    initial_delay_ms: int = 1000
    max_delay_ms: int = 60000
    backoff_multiplier: float = 2.0
    jitter_factor: float = 0.1


@dataclass
class QueueMessage[T]:
    """Message in retry queue."""
    id: str
    payload: T
    created_at: datetime
    status: MessageStatus = MessageStatus.PENDING
    retry_count: int = 0
    next_retry_at: datetime | None = None
    last_error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProcessingResult:
    """Result of message processing."""
    success: bool
    error: str | None = None
    should_retry: bool = True


class MessageHandler[T](Protocol):
    """Protocol for message handlers."""

    async def handle(self, message: QueueMessage[T]) -> ProcessingResult: ...


class QueueBackend[T](Protocol):
    """Protocol for queue storage backend."""

    async def enqueue(self, message: QueueMessage[T]) -> None: ...
    async def dequeue(self, limit: int) -> list[QueueMessage[T]]: ...
    async def update(self, message: QueueMessage[T]) -> None: ...
    async def move_to_dlq(self, message: QueueMessage[T]) -> None: ...
    async def get_dlq_messages(self, limit: int) -> list[QueueMessage[T]]: ...
    async def requeue_from_dlq(self, message_id: str) -> bool: ...


class RetryQueue[T]:
    """Retry queue with exponential backoff and DLQ."""

    def __init__(
        self,
        backend: QueueBackend[T],
        handler: MessageHandler[T],
        config: RetryConfig | None = None
    ) -> None:
        self._backend = backend
        self._handler = handler
        self._config = config or RetryConfig()
        self._running = False
        self._hooks: dict[str, list[Callable[[QueueMessage[T]], Awaitable[None]]]] = {
            "before_process": [],
            "after_process": [],
            "on_dlq": [],
        }

    def register_hook(
        self,
        event: str,
        callback: Callable[[QueueMessage[T]], Awaitable[None]]
    ) -> None:
        """Register a hook for queue events."""
        if event in self._hooks:
            self._hooks[event].append(callback)

    async def _run_hooks(self, event: str, message: QueueMessage[T]) -> None:
        for hook in self._hooks.get(event, []):
            await hook(message)

    def _calculate_delay(self, retry_count: int) -> int:
        """Calculate delay with exponential backoff and jitter."""
        import random
        delay = self._config.initial_delay_ms * (
            self._config.backoff_multiplier ** retry_count
        )
        delay = min(delay, self._config.max_delay_ms)

        jitter = delay * self._config.jitter_factor
        delay += random.uniform(-jitter, jitter)

        return int(max(0, delay))

    async def enqueue(
        self,
        payload: T,
        metadata: dict[str, Any] | None = None
    ) -> QueueMessage[T]:
        """Add a message to the queue."""
        import uuid
        message = QueueMessage(
            id=str(uuid.uuid4()),
            payload=payload,
            created_at=datetime.now(UTC),
            metadata=metadata or {}
        )
        await self._backend.enqueue(message)
        return message

    async def process_one(self) -> bool:
        """Process a single message."""
        messages = await self._backend.dequeue(1)
        if not messages:
            return False

        message = messages[0]
        await self._process_message(message)
        return True

    async def _process_message(self, message: QueueMessage[T]) -> None:
        """Process a message with retry logic."""
        message.status = MessageStatus.PROCESSING
        await self._backend.update(message)
        await self._run_hooks("before_process", message)

        try:
            result = await self._handler.handle(message)

            if result.success:
                message.status = MessageStatus.COMPLETED
                await self._backend.update(message)
            elif result.should_retry and message.retry_count < self._config.max_retries:
                message.retry_count += 1
                message.last_error = result.error
                message.status = MessageStatus.PENDING
                delay = self._calculate_delay(message.retry_count)
                message.next_retry_at = datetime.now(UTC) + timedelta(milliseconds=delay)
                await self._backend.update(message)
            else:
                message.status = MessageStatus.DEAD_LETTER
                message.last_error = result.error
                await self._backend.move_to_dlq(message)
                await self._run_hooks("on_dlq", message)

        except Exception as e:
            message.last_error = str(e)
            if message.retry_count < self._config.max_retries:
                message.retry_count += 1
                message.status = MessageStatus.PENDING
                delay = self._calculate_delay(message.retry_count)
                message.next_retry_at = datetime.now(UTC) + timedelta(milliseconds=delay)
                await self._backend.update(message)
            else:
                message.status = MessageStatus.DEAD_LETTER
                await self._backend.move_to_dlq(message)
                await self._run_hooks("on_dlq", message)

        await self._run_hooks("after_process", message)

    async def process_batch(self, batch_size: int = 10) -> int:
        """Process a batch of messages."""
        messages = await self._backend.dequeue(batch_size)
        for message in messages:
            await self._process_message(message)
        return len(messages)

    async def start(self, poll_interval_ms: int = 1000) -> None:
        """Start processing messages."""
        self._running = True
        while self._running:
            processed = await self.process_batch()
            if processed == 0:
                await asyncio.sleep(poll_interval_ms / 1000)

    def stop(self) -> None:
        """Stop processing messages."""
        self._running = False

    async def get_dlq_messages(self, limit: int = 100) -> list[QueueMessage[T]]:
        """Get messages from dead letter queue."""
        return await self._backend.get_dlq_messages(limit)

    async def requeue_from_dlq(self, message_id: str) -> bool:
        """Requeue a message from DLQ."""
        return await self._backend.requeue_from_dlq(message_id)

    async def requeue_all_dlq(self) -> int:
        """Requeue all messages from DLQ."""
        messages = await self._backend.get_dlq_messages(1000)
        count = 0
        for message in messages:
            if await self._backend.requeue_from_dlq(message.id):
                count += 1
        return count


class InMemoryQueueBackend[T]:
    """In-memory queue backend for testing."""

    def __init__(self) -> None:
        self._queue: list[QueueMessage[T]] = []
        self._dlq: list[QueueMessage[T]] = []

    async def enqueue(self, message: QueueMessage[T]) -> None:
        self._queue.append(message)

    async def dequeue(self, limit: int) -> list[QueueMessage[T]]:
        now = datetime.now(UTC)
        ready = [
            m for m in self._queue
            if m.status == MessageStatus.PENDING and
            (m.next_retry_at is None or m.next_retry_at <= now)
        ][:limit]
        return ready

    async def update(self, message: QueueMessage[T]) -> None:
        for i, m in enumerate(self._queue):
            if m.id == message.id:
                self._queue[i] = message
                break

    async def move_to_dlq(self, message: QueueMessage[T]) -> None:
        self._queue = [m for m in self._queue if m.id != message.id]
        self._dlq.append(message)

    async def get_dlq_messages(self, limit: int) -> list[QueueMessage[T]]:
        return self._dlq[:limit]

    async def requeue_from_dlq(self, message_id: str) -> bool:
        for i, m in enumerate(self._dlq):
            if m.id == message_id:
                m.status = MessageStatus.PENDING
                m.retry_count = 0
                m.next_retry_at = None
                self._queue.append(m)
                self._dlq.pop(i)
                return True
        return False
