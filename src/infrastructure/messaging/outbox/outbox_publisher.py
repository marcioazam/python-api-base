"""Outbox publisher for reliable message delivery.

**Feature: python-api-base-2025-validation**
**Validates: Requirements 33.3, 33.4, 33.5**
"""

import asyncio
import logging
import random
from collections.abc import Callable, Sequence
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol
from uuid import UUID

from infrastructure.messaging.outbox.outbox_message import (
    OutboxMessage,
    OutboxMessageStatus,
)

logger = logging.getLogger(__name__)


class IOutboxRepository(Protocol):
    """Protocol for outbox repository (Dependency Inversion).

    Allows swapping in-memory implementation for SQLModel in production.
    """

    async def save(self, message: OutboxMessage) -> OutboxMessage: ...
    async def get_by_id(self, message_id: UUID) -> OutboxMessage | None: ...
    async def get_pending(
        self, limit: int = 100, include_failed: bool = True
    ) -> Sequence[OutboxMessage]: ...
    async def update(self, message: OutboxMessage) -> OutboxMessage: ...
    async def mark_processed(self, message_id: UUID) -> bool: ...
    async def mark_failed(
        self, message_id: UUID, error: str, next_retry: datetime | None = None
    ) -> bool: ...
    async def is_duplicate(self, idempotency_key: str) -> bool: ...
    async def get_dead_letters(self, limit: int = 100) -> Sequence[OutboxMessage]: ...


class OutboxPublisher:
    """Background publisher for outbox messages.

    Polls the outbox table and publishes messages to the event bus
    or external message broker with retry logic and exponential backoff.

    Features:
    - Exponential backoff with jitter (prevents thundering herd)
    - Idempotency key deduplication
    - Dead letter queue support
    - Metrics hooks for observability
    - Graceful shutdown

    **Feature: python-api-base-2025-validation**
    **Validates: Requirements 33.3, 33.4, 33.5**
    """

    def __init__(
        self,
        repository: IOutboxRepository,
        publish_fn: Callable[[dict[str, Any]], Any] | None = None,
        *,
        poll_interval: float = 5.0,
        batch_size: int = 100,
        base_delay: float = 1.0,
        max_delay: float = 300.0,
        jitter_factor: float = 0.1,
        on_publish: Callable[[OutboxMessage], None] | None = None,
        on_failure: Callable[[OutboxMessage, Exception], None] | None = None,
    ) -> None:
        """Initialize outbox publisher.

        Args:
            repository: Outbox repository for message persistence.
            publish_fn: Function to publish messages (async or sync).
            poll_interval: Seconds between polling. Default 5.0.
            batch_size: Messages per batch. Default 100.
            base_delay: Base delay for exponential backoff. Default 1.0.
            max_delay: Maximum delay between retries. Default 300.0.
            jitter_factor: Random jitter factor (0-1). Default 0.1.
            on_publish: Callback when message published (for metrics).
            on_failure: Callback when message fails (for metrics).
        """
        self._repository = repository
        self._publish_fn = publish_fn
        self._poll_interval = poll_interval
        self._batch_size = batch_size
        self._base_delay = base_delay
        self._max_delay = max_delay
        self._jitter_factor = jitter_factor
        self._on_publish = on_publish
        self._on_failure = on_failure
        self._running = False
        self._task: asyncio.Task[None] | None = None
        self._published_count = 0
        self._failed_count = 0

    async def start(self) -> None:
        """Start the background publisher."""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._poll_loop())
        logger.info("Outbox publisher started")

    async def stop(self) -> None:
        """Stop the background publisher."""
        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        logger.info("Outbox publisher stopped")

    async def _poll_loop(self) -> None:
        """Main polling loop."""
        while self._running:
            try:
                published = await self.publish_pending()
                if published > 0:
                    logger.debug(f"Published {published} outbox messages")
            except Exception as e:
                logger.error(f"Error in outbox publisher: {e}")

            await asyncio.sleep(self._poll_interval)

    async def publish_pending(self) -> int:
        """Publish pending messages.

        Returns:
            Number of messages published.
        """
        messages = await self._repository.get_pending(limit=self._batch_size)

        if not messages:
            return 0

        published = 0
        for message in messages:
            try:
                await self._publish_message(message)
                published += 1
            except Exception as e:
                logger.warning(f"Failed to publish message {message.id}: {e}")

        return published

    async def _publish_message(self, message: OutboxMessage) -> None:
        """Publish a single message.

        Args:
            message: Message to publish.
        """
        # Check for duplicate
        if message.idempotency_key:
            is_dup = await self._repository.is_duplicate(message.idempotency_key)
            if is_dup:
                logger.debug(f"Skipping duplicate message: {message.idempotency_key}")
                await self._repository.mark_processed(message.id)
                return

        # Mark as processing
        message.mark_processing()
        await self._repository.update(message)

        try:
            # Publish
            if self._publish_fn:
                event_data = message.to_event_dict()
                result = self._publish_fn(event_data)

                # Handle async publish function
                if asyncio.iscoroutine(result):
                    await result

            # Mark as published
            await self._repository.mark_processed(message.id)
            self._published_count += 1

            # Metrics callback
            if self._on_publish:
                self._on_publish(message)

            logger.debug(
                "Published outbox message",
                extra={
                    "message_id": str(message.id),
                    "event_type": message.event_type,
                    "correlation_id": message.correlation_id,
                },
            )

        except Exception as e:
            # Calculate next retry time with exponential backoff
            delay = self._calculate_backoff(message.retry_count)
            next_retry = datetime.now(UTC) + timedelta(seconds=delay)

            await self._repository.mark_failed(
                message.id,
                str(e),
                next_retry,
            )

            self._failed_count += 1

            # Metrics callback
            if self._on_failure:
                self._on_failure(message, e)

            log_extra = {
                "message_id": str(message.id),
                "event_type": message.event_type,
                "correlation_id": message.correlation_id,
                "retry_count": message.retry_count + 1,
                "error": str(e),
            }

            if message.retry_count + 1 >= message.max_retries:
                logger.error(
                    "Outbox message moved to dead letter",
                    extra={**log_extra, "status": "dead_letter"},
                )
            else:
                logger.warning(
                    "Outbox message failed, will retry",
                    extra={**log_extra, "next_retry_seconds": delay},
                )

            raise

    def _calculate_backoff(self, retry_count: int) -> float:
        """Calculate exponential backoff delay with jitter.

        Uses jitter to prevent thundering herd problem when multiple
        publishers retry at the same time.

        Args:
            retry_count: Current retry count.

        Returns:
            Delay in seconds with random jitter.
        """
        delay = self._base_delay * (2**retry_count)
        delay = min(delay, self._max_delay)

        # Add jitter: delay * (1 ± jitter_factor)
        jitter = delay * self._jitter_factor * (2 * random.random() - 1)
        return max(0.1, delay + jitter)  # Minimum 100ms

    async def publish_one(self, message: OutboxMessage) -> bool:
        """Publish a single message immediately.

        Args:
            message: Message to publish.

        Returns:
            True if published successfully, False otherwise.
        """
        try:
            await self._publish_message(message)
            return True
        except Exception:
            return False

    async def retry_dead_letters(self, limit: int = 10) -> int:
        """Retry dead letter messages.

        Args:
            limit: Maximum messages to retry.

        Returns:
            Number of messages retried.
        """
        from infrastructure.messaging.outbox.outbox_message import OutboxMessageStatus

        dead_letters = await self._repository.get_dead_letters(limit)

        retried = 0
        for msg in dead_letters:
            # Reset for retry
            msg.retry_count = 0
            msg.status = OutboxMessageStatus.PENDING
            msg.last_error = None
            msg.next_retry_at = None

            await self._repository.update(msg)
            retried += 1

        return retried

    @property
    def is_running(self) -> bool:
        """Check if publisher is running."""
        return self._running

    @property
    def published_count(self) -> int:
        """Total messages published since start."""
        return self._published_count

    @property
    def failed_count(self) -> int:
        """Total message failures since start."""
        return self._failed_count

    def get_stats(self) -> dict[str, Any]:
        """Get publisher statistics for monitoring.

        Returns:
            Dictionary with publisher stats.
        """
        return {
            "is_running": self._running,
            "published_count": self._published_count,
            "failed_count": self._failed_count,
            "poll_interval": self._poll_interval,
            "batch_size": self._batch_size,
        }


# =============================================================================
# Context Manager Support
# =============================================================================


class OutboxPublisherContext:
    """Context manager for outbox publisher lifecycle."""

    def __init__(self, publisher: OutboxPublisher) -> None:
        self._publisher = publisher

    async def __aenter__(self) -> OutboxPublisher:
        await self._publisher.start()
        return self._publisher

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self._publisher.stop()
