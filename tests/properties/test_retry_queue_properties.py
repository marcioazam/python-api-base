"""Property-based tests for Retry Queue Pattern.

**Feature: api-architecture-analysis, Property: Retry queue operations**
**Validates: Requirements 21.4**
"""

import pytest
from hypothesis import given, strategies as st, settings
from datetime import datetime
from dataclasses import dataclass

from my_app.infrastructure.messaging.retry_queue import (
    RetryQueue,
    RetryConfig,
    QueueMessage,
    MessageStatus,
    ProcessingResult,
    InMemoryQueueBackend,
)


@dataclass
class RetryPayload:
    """Payload for retry queue testing."""
    id: str
    data: str


class SuccessHandler:
    """Handler that always succeeds."""

    async def handle(self, message: QueueMessage[RetryPayload]) -> ProcessingResult:
        return ProcessingResult(success=True)


class FailHandler:
    """Handler that always fails."""

    async def handle(self, message: QueueMessage[RetryPayload]) -> ProcessingResult:
        return ProcessingResult(success=False, error="Test failure", should_retry=True)


class TestRetryQueueProperties:
    """Property tests for retry queue."""

    @given(
        st.text(min_size=1, max_size=20),
        st.text(min_size=1, max_size=100)
    )
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_enqueue_creates_pending_message(
        self,
        id: str,
        data: str
    ) -> None:
        """Enqueue creates message with pending status."""
        backend: InMemoryQueueBackend[RetryPayload] = InMemoryQueueBackend()
        handler = SuccessHandler()
        queue: RetryQueue[RetryPayload] = RetryQueue(backend, handler)

        payload = RetryPayload(id=id, data=data)
        message = await queue.enqueue(payload)

        assert message.status == MessageStatus.PENDING
        assert message.retry_count == 0

    @given(
        st.text(min_size=1, max_size=20),
        st.text(min_size=1, max_size=100)
    )
    @settings(max_examples=50)
    @pytest.mark.asyncio
    async def test_successful_processing_completes(
        self,
        id: str,
        data: str
    ) -> None:
        """Successful processing marks message as completed."""
        backend: InMemoryQueueBackend[RetryPayload] = InMemoryQueueBackend()
        handler = SuccessHandler()
        queue: RetryQueue[RetryPayload] = RetryQueue(backend, handler)

        payload = RetryPayload(id=id, data=data)
        await queue.enqueue(payload)
        await queue.process_one()

        # Message should be completed
        messages = await backend.dequeue(10)
        pending = [m for m in messages if m.status == MessageStatus.PENDING]
        assert len(pending) == 0

    @given(st.integers(min_value=1, max_value=5))
    @settings(max_examples=50)
    @pytest.mark.asyncio
    async def test_failed_processing_retries(self, max_retries: int) -> None:
        """Failed processing increments retry count."""
        backend: InMemoryQueueBackend[RetryPayload] = InMemoryQueueBackend()
        handler = FailHandler()
        config = RetryConfig(max_retries=max_retries, initial_delay_ms=0)
        queue: RetryQueue[RetryPayload] = RetryQueue(backend, handler, config)

        payload = RetryPayload(id="test", data="data")
        message = await queue.enqueue(payload)

        # Process once
        await queue.process_one()

        # Check retry count increased
        messages = await backend.dequeue(10)
        if messages:
            assert messages[0].retry_count == 1

    @given(st.integers(min_value=1, max_value=3))
    @settings(max_examples=30)
    @pytest.mark.asyncio
    async def test_max_retries_moves_to_dlq(self, max_retries: int) -> None:
        """Exceeding max retries moves to DLQ."""
        backend: InMemoryQueueBackend[RetryPayload] = InMemoryQueueBackend()
        handler = FailHandler()
        config = RetryConfig(max_retries=max_retries, initial_delay_ms=0)
        queue: RetryQueue[RetryPayload] = RetryQueue(backend, handler, config)

        payload = RetryPayload(id="test", data="data")
        await queue.enqueue(payload)

        # Process until DLQ
        for _ in range(max_retries + 1):
            await queue.process_one()

        dlq_messages = await queue.get_dlq_messages()
        assert len(dlq_messages) == 1

    @given(
        st.integers(min_value=100, max_value=1000),
        st.floats(min_value=1.5, max_value=3.0)
    )
    @settings(max_examples=50)
    def test_delay_calculation_exponential(
        self,
        initial_delay: int,
        multiplier: float
    ) -> None:
        """Delay increases exponentially."""
        backend: InMemoryQueueBackend[TestPayload] = InMemoryQueueBackend()
        handler = SuccessHandler()
        config = RetryConfig(
            initial_delay_ms=initial_delay,
            backoff_multiplier=multiplier,
            max_delay_ms=1000000,
            jitter_factor=0
        )
        queue: RetryQueue[TestPayload] = RetryQueue(backend, handler, config)

        delay_0 = queue._calculate_delay(0)
        delay_1 = queue._calculate_delay(1)
        delay_2 = queue._calculate_delay(2)

        assert delay_1 > delay_0
        assert delay_2 > delay_1

    @given(st.integers(min_value=1, max_value=5))
    @settings(max_examples=30)
    @pytest.mark.asyncio
    async def test_requeue_from_dlq(self, count: int) -> None:
        """Requeue from DLQ resets message."""
        backend: InMemoryQueueBackend[RetryPayload] = InMemoryQueueBackend()
        handler = FailHandler()
        config = RetryConfig(max_retries=0, initial_delay_ms=0)
        queue: RetryQueue[RetryPayload] = RetryQueue(backend, handler, config)

        # Add messages and move to DLQ
        for i in range(count):
            await queue.enqueue(RetryPayload(id=str(i), data="data"))
            await queue.process_one()

        dlq_before = await queue.get_dlq_messages()
        assert len(dlq_before) == count

        # Requeue all
        requeued = await queue.requeue_all_dlq()
        assert requeued == count

        dlq_after = await queue.get_dlq_messages()
        assert len(dlq_after) == 0
