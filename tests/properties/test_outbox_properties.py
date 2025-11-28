"""Property-based tests for Outbox Pattern.

**Feature: api-architecture-analysis, Property 7: Outbox pattern**
**Validates: Requirements 9.5**
"""

from datetime import datetime, timedelta

import pytest
from hypothesis import given, settings, strategies as st

from my_api.shared.outbox import (
    InMemoryOutboxRepository,
    MockEventPublisher,
    OutboxEntry,
    OutboxService,
    OutboxStatus,
)


identifier_strategy = st.text(
    alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz_"),
    min_size=1,
    max_size=20,
)


class TestOutboxEntry:
    """Tests for OutboxEntry."""

    @given(
        aggregate_type=identifier_strategy,
        aggregate_id=identifier_strategy,
        event_type=identifier_strategy,
    )
    @settings(max_examples=50)
    def test_create_generates_id(
        self, aggregate_type: str, aggregate_id: str, event_type: str
    ):
        """create should generate a unique ID."""
        entry = OutboxEntry.create(
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            event_type=event_type,
            payload={"test": "data"},
        )
        assert entry.id is not None
        assert len(entry.id) > 0

    @given(
        aggregate_type=identifier_strategy,
        aggregate_id=identifier_strategy,
        event_type=identifier_strategy,
    )
    @settings(max_examples=50)
    def test_create_sets_pending_status(
        self, aggregate_type: str, aggregate_id: str, event_type: str
    ):
        """create should set status to PENDING."""
        entry = OutboxEntry.create(
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            event_type=event_type,
            payload={},
        )
        assert entry.status == OutboxStatus.PENDING

    def test_mark_processing(self):
        """mark_processing should set status to PROCESSING."""
        entry = OutboxEntry.create("Type", "123", "Event", {})
        entry.mark_processing()
        assert entry.status == OutboxStatus.PROCESSING

    def test_mark_published(self):
        """mark_published should set status and processed_at."""
        entry = OutboxEntry.create("Type", "123", "Event", {})
        entry.mark_published()
        assert entry.status == OutboxStatus.PUBLISHED
        assert entry.processed_at is not None

    def test_mark_failed_increments_retry(self):
        """mark_failed should increment retry count."""
        entry = OutboxEntry.create("Type", "123", "Event", {})
        entry.mark_failed("Error")
        assert entry.retry_count == 1
        assert entry.error_message == "Error"

    def test_mark_failed_sets_failed_after_max_retries(self):
        """mark_failed should set FAILED after max retries."""
        entry = OutboxEntry.create("Type", "123", "Event", {})
        entry.max_retries = 2
        entry.mark_failed("Error 1")
        assert entry.status == OutboxStatus.PENDING
        entry.mark_failed("Error 2")
        assert entry.status == OutboxStatus.FAILED

    def test_can_retry(self):
        """can_retry should return True if under max retries."""
        entry = OutboxEntry.create("Type", "123", "Event", {})
        entry.max_retries = 3
        assert entry.can_retry is True
        entry.retry_count = 3
        assert entry.can_retry is False

    def test_to_dict(self):
        """to_dict should contain all fields."""
        entry = OutboxEntry.create("Type", "123", "Event", {"key": "value"})
        d = entry.to_dict()
        assert d["aggregate_type"] == "Type"
        assert d["aggregate_id"] == "123"
        assert d["event_type"] == "Event"
        assert d["payload"] == {"key": "value"}


class TestInMemoryOutboxRepository:
    """Tests for InMemoryOutboxRepository."""

    @pytest.mark.asyncio
    async def test_save_and_get_pending(self):
        """save should store entry retrievable by get_pending."""
        repo = InMemoryOutboxRepository()
        entry = OutboxEntry.create("Type", "123", "Event", {})
        await repo.save(entry)
        pending = await repo.get_pending()
        assert len(pending) == 1
        assert pending[0].id == entry.id

    @pytest.mark.asyncio
    async def test_get_pending_excludes_non_pending(self):
        """get_pending should exclude non-pending entries."""
        repo = InMemoryOutboxRepository()
        entry1 = OutboxEntry.create("Type", "1", "Event", {})
        entry2 = OutboxEntry.create("Type", "2", "Event", {})
        entry2.mark_published()
        await repo.save(entry1)
        await repo.save(entry2)
        pending = await repo.get_pending()
        assert len(pending) == 1
        assert pending[0].id == entry1.id

    @pytest.mark.asyncio
    async def test_get_pending_respects_limit(self):
        """get_pending should respect limit."""
        repo = InMemoryOutboxRepository()
        for i in range(5):
            await repo.save(OutboxEntry.create("Type", str(i), "Event", {}))
        pending = await repo.get_pending(limit=3)
        assert len(pending) == 3

    @pytest.mark.asyncio
    async def test_update_modifies_entry(self):
        """update should modify existing entry."""
        repo = InMemoryOutboxRepository()
        entry = OutboxEntry.create("Type", "123", "Event", {})
        await repo.save(entry)
        entry.mark_published()
        await repo.update(entry)
        pending = await repo.get_pending()
        assert len(pending) == 0

    @pytest.mark.asyncio
    async def test_delete_published(self):
        """delete_published should remove old published entries."""
        repo = InMemoryOutboxRepository()
        entry = OutboxEntry.create("Type", "123", "Event", {})
        entry.mark_published()
        entry.processed_at = datetime.utcnow() - timedelta(days=2)
        await repo.save(entry)
        deleted = await repo.delete_published(datetime.utcnow() - timedelta(days=1))
        assert deleted == 1
        assert repo.count() == 0

    def test_count_by_status(self):
        """count_by_status should return correct count."""
        repo = InMemoryOutboxRepository()
        repo._entries["1"] = OutboxEntry.create("Type", "1", "Event", {})
        entry2 = OutboxEntry.create("Type", "2", "Event", {})
        entry2.mark_published()
        repo._entries["2"] = entry2
        assert repo.count_by_status(OutboxStatus.PENDING) == 1
        assert repo.count_by_status(OutboxStatus.PUBLISHED) == 1


class TestOutboxService:
    """Tests for OutboxService."""

    @pytest.mark.asyncio
    async def test_add_event(self):
        """add_event should create and save entry."""
        repo = InMemoryOutboxRepository()
        publisher = MockEventPublisher()
        service = OutboxService(repo, publisher)
        entry = await service.add_event("Order", "123", "OrderCreated", {"total": 100})
        assert entry.aggregate_type == "Order"
        assert entry.event_type == "OrderCreated"
        assert repo.count() == 1

    @pytest.mark.asyncio
    async def test_process_pending_success(self):
        """process_pending should publish and mark entries."""
        repo = InMemoryOutboxRepository()
        publisher = MockEventPublisher()
        service = OutboxService(repo, publisher)
        await service.add_event("Order", "123", "OrderCreated", {"total": 100})
        success, failed = await service.process_pending()
        assert success == 1
        assert failed == 0
        assert len(publisher.published_events) == 1

    @pytest.mark.asyncio
    async def test_process_pending_failure(self):
        """process_pending should handle failures."""
        repo = InMemoryOutboxRepository()
        publisher = MockEventPublisher(should_fail=True)
        service = OutboxService(repo, publisher)
        await service.add_event("Order", "123", "OrderCreated", {"total": 100})
        success, failed = await service.process_pending()
        assert success == 0
        assert failed == 1

    @pytest.mark.asyncio
    async def test_cleanup(self):
        """cleanup should remove old published entries."""
        repo = InMemoryOutboxRepository()
        publisher = MockEventPublisher()
        service = OutboxService(repo, publisher)
        entry = await service.add_event("Order", "123", "OrderCreated", {})
        entry.mark_published()
        entry.processed_at = datetime.utcnow() - timedelta(days=10)
        await repo.update(entry)
        deleted = await service.cleanup(datetime.utcnow() - timedelta(days=7))
        assert deleted == 1


class TestMockEventPublisher:
    """Tests for MockEventPublisher."""

    @pytest.mark.asyncio
    async def test_publish_success(self):
        """publish should return True and store event."""
        publisher = MockEventPublisher()
        result = await publisher.publish("TestEvent", {"key": "value"})
        assert result is True
        assert len(publisher.published_events) == 1

    @pytest.mark.asyncio
    async def test_publish_failure(self):
        """publish should return False when configured to fail."""
        publisher = MockEventPublisher(should_fail=True)
        result = await publisher.publish("TestEvent", {"key": "value"})
        assert result is False
        assert len(publisher.published_events) == 0

    def test_clear(self):
        """clear should remove all published events."""
        publisher = MockEventPublisher()
        publisher._published.append(("Event", {}))
        publisher.clear()
        assert len(publisher.published_events) == 0
