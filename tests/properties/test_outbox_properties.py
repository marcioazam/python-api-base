"""Property-based tests for Outbox Pattern.

**Feature: python-api-base-2025-validation**
**Property 28: Outbox Transactional Atomicity**
**Validates: Requirements 33.1, 33.2**
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from hypothesis import given, settings, strategies as st

from infrastructure.messaging.outbox.outbox_message import (
    OutboxMessage,
    OutboxMessageStatus,
    create_outbox_message,
)
from infrastructure.messaging.outbox.outbox_repository import OutboxRepository


# =============================================================================
# Property 28: Outbox Transactional Atomicity
# **Feature: python-api-base-2025-validation, Property 28: Outbox Transactional Atomicity**
# **Validates: Requirements 33.1, 33.2**
# =============================================================================


class TestOutboxTransactionalAtomicity:
    """Property tests for outbox transactional atomicity.

    **Feature: python-api-base-2025-validation, Property 28: Outbox Transactional Atomicity**
    **Validates: Requirements 33.1, 33.2**
    """

    @given(
        aggregate_type=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("L", "N"))),
        aggregate_id=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("L", "N"))),
        event_type=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("L", "N"))),
    )
    @settings(max_examples=100)
    def test_outbox_message_creation_preserves_data(
        self, aggregate_type: str, aggregate_id: str, event_type: str
    ) -> None:
        """
        **Feature: python-api-base-2025-validation, Property 28: Outbox Transactional Atomicity**
        **Validates: Requirements 33.1, 33.2**

        *For any* outbox message created, all fields SHALL be preserved.
        """
        message = create_outbox_message(
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            event_type=event_type,
            payload={"test": "data"},
        )

        assert message.aggregate_type == aggregate_type
        assert message.aggregate_id == aggregate_id
        assert message.event_type == event_type
        assert message.payload == {"test": "data"}
        assert message.status == OutboxMessageStatus.PENDING
        assert message.idempotency_key is not None

    @pytest.mark.asyncio
    @given(st.integers(min_value=1, max_value=20))
    @settings(max_examples=50)
    async def test_repository_save_and_retrieve(self, count: int) -> None:
        """
        **Feature: python-api-base-2025-validation, Property 28: Outbox Transactional Atomicity**
        **Validates: Requirements 33.1, 33.2**

        *For any* N messages saved to repository, all N SHALL be retrievable.
        """
        repo = OutboxRepository()

        messages = [
            create_outbox_message(
                aggregate_type="Test",
                aggregate_id=str(i),
                event_type="TestEvent",
                payload={"index": i},
            )
            for i in range(count)
        ]

        for msg in messages:
            await repo.save(msg)

        pending = await repo.get_pending(limit=count + 10)
        assert len(pending) == count

    @pytest.mark.asyncio
    async def test_idempotency_key_prevents_duplicates(self) -> None:
        """
        **Feature: python-api-base-2025-validation, Property 28: Outbox Transactional Atomicity**
        **Validates: Requirements 33.2**

        Idempotency key SHALL prevent duplicate processing.
        """
        repo = OutboxRepository()
        idempotency_key = f"test-key-{uuid4()}"

        message = OutboxMessage(
            aggregate_type="Test",
            aggregate_id="1",
            event_type="TestEvent",
            payload={},
            idempotency_key=idempotency_key,
        )

        await repo.save(message)
        await repo.mark_processed(message.id)

        # Check duplicate detection
        is_dup = await repo.is_duplicate(idempotency_key)
        assert is_dup is True

        # New key should not be duplicate
        is_new_dup = await repo.is_duplicate(f"new-key-{uuid4()}")
        assert is_new_dup is False

    @pytest.mark.asyncio
    async def test_mark_processed_updates_status(self) -> None:
        """
        **Feature: python-api-base-2025-validation, Property 28: Outbox Transactional Atomicity**
        **Validates: Requirements 33.1**

        After mark_processed, message status SHALL be PUBLISHED.
        """
        repo = OutboxRepository()

        message = create_outbox_message(
            aggregate_type="Test",
            aggregate_id="1",
            event_type="TestEvent",
            payload={},
        )

        await repo.save(message)
        await repo.mark_processed(message.id)

        retrieved = await repo.get_by_id(message.id)
        assert retrieved is not None
        assert retrieved.status == OutboxMessageStatus.PUBLISHED
        assert retrieved.processed_at is not None

    @pytest.mark.asyncio
    async def test_mark_failed_increments_retry_count(self) -> None:
        """
        **Feature: python-api-base-2025-validation, Property 28: Outbox Transactional Atomicity**
        **Validates: Requirements 33.1**

        After mark_failed, retry_count SHALL increment.
        """
        repo = OutboxRepository()

        message = create_outbox_message(
            aggregate_type="Test",
            aggregate_id="1",
            event_type="TestEvent",
            payload={},
        )

        await repo.save(message)
        initial_retry = message.retry_count

        await repo.mark_failed(message.id, "Test error")

        retrieved = await repo.get_by_id(message.id)
        assert retrieved is not None
        assert retrieved.retry_count == initial_retry + 1
        assert retrieved.last_error == "Test error"

    @pytest.mark.asyncio
    async def test_max_retries_moves_to_dead_letter(self) -> None:
        """
        **Feature: python-api-base-2025-validation, Property 28: Outbox Transactional Atomicity**
        **Validates: Requirements 33.1**

        After max_retries failures, message SHALL move to DEAD_LETTER.
        """
        repo = OutboxRepository()

        message = OutboxMessage(
            aggregate_type="Test",
            aggregate_id="1",
            event_type="TestEvent",
            payload={},
            max_retries=3,
        )

        await repo.save(message)

        # Fail max_retries times
        for i in range(3):
            await repo.mark_failed(message.id, f"Error {i + 1}")

        retrieved = await repo.get_by_id(message.id)
        assert retrieved is not None
        assert retrieved.status == OutboxMessageStatus.DEAD_LETTER

    @given(
        payload=st.dictionaries(
            st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=("L",))),
            st.one_of(st.integers(), st.text(max_size=50), st.booleans()),
            max_size=10,
        )
    )
    @settings(max_examples=50)
    def test_to_event_dict_preserves_payload(self, payload: dict) -> None:
        """
        **Feature: python-api-base-2025-validation, Property 28: Outbox Transactional Atomicity**
        **Validates: Requirements 33.1**

        *For any* payload, to_event_dict SHALL preserve the payload data.
        """
        message = OutboxMessage(
            aggregate_type="Test",
            aggregate_id="1",
            event_type="TestEvent",
            payload=payload,
        )

        event_dict = message.to_event_dict()

        assert event_dict["payload"] == payload
        assert event_dict["type"] == "TestEvent"
        assert event_dict["aggregate_type"] == "Test"
        assert event_dict["aggregate_id"] == "1"

