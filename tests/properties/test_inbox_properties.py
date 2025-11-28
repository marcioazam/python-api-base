"""Property-based tests for Inbox Pattern.

**Feature: api-architecture-analysis, Property 9: Inbox pattern**
**Validates: Requirements 9.5**
"""

from datetime import datetime, timedelta

import pytest
from hypothesis import given, settings, strategies as st

from my_api.shared.inbox import (
    InboxEntry,
    InboxService,
    InboxStatus,
    InMemoryInboxRepository,
    MockMessageHandler,
)


identifier_strategy = st.text(
    alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789_"),
    min_size=1,
    max_size=20,
)


class TestInboxEntry:
    """Tests for InboxEntry."""

    @given(
        message_id=identifier_strategy,
        message_type=identifier_strategy,
    )
    @settings(max_examples=50)
    def test_create_generates_idempotency_key(
        self, message_id: str, message_type: str
    ):
        """create should generate idempotency key."""
        entry = InboxEntry.create(
            message_id=message_id,
            message_type=message_type,
            payload={"test": "data"},
        )
        assert entry.idempotency_key is not None
        assert len(entry.idempotency_key) > 0

    @given(
        message_id=identifier_strategy,
        message_type=identifier_strategy,
    )
    @settings(max_examples=50)
    def test_same_content_same_idempotency_key(
        self, message_id: str, message_type: str
    ):
        """Same content should produce same idempotency key."""
        payload = {"key": "value"}
        entry1 = InboxEntry.create(message_id, message_type, payload)
        entry2 = InboxEntry.create(message_id, message_type, payload)
        assert entry1.idempotency_key == entry2.idempotency_key

    def test_mark_processing(self):
        """mark_processing should set status."""
        entry = InboxEntry.create("id", "type", {})
        entry.mark_processing()
        assert entry.status == InboxStatus.PROCESSING

    def test_mark_processed(self):
        """mark_processed should set status and timestamp."""
        entry = InboxEntry.create("id", "type", {})
        entry.mark_processed()
        assert entry.status == InboxStatus.PROCESSED
        assert entry.processed_at is not None

    def test_mark_failed(self):
        """mark_failed should set status and error."""
        entry = InboxEntry.create("id", "type", {})
        entry.mark_failed("Error message")
        assert entry.status == InboxStatus.FAILED
        assert entry.error_message == "Error message"

    def test_to_dict(self):
        """to_dict should contain all fields."""
        entry = InboxEntry.create("id", "type", {"key": "value"})
        d = entry.to_dict()
        assert d["message_id"] == "id"
        assert d["message_type"] == "type"
        assert d["payload"] == {"key": "value"}


class TestInMemoryInboxRepository:
    """Tests for InMemoryInboxRepository."""

    @pytest.mark.asyncio
    async def test_save_and_get_by_id(self):
        """save should store entry retrievable by get_by_id."""
        repo = InMemoryInboxRepository()
        entry = InboxEntry.create("msg1", "type", {})
        await repo.save(entry)
        retrieved = await repo.get_by_id("msg1")
        assert retrieved is not None
        assert retrieved.message_id == "msg1"

    @pytest.mark.asyncio
    async def test_get_by_idempotency_key(self):
        """get_by_idempotency_key should find entry."""
        repo = InMemoryInboxRepository()
        entry = InboxEntry.create("msg1", "type", {})
        await repo.save(entry)
        retrieved = await repo.get_by_idempotency_key(entry.idempotency_key or "")
        assert retrieved is not None
        assert retrieved.message_id == "msg1"

    @pytest.mark.asyncio
    async def test_update_modifies_entry(self):
        """update should modify existing entry."""
        repo = InMemoryInboxRepository()
        entry = InboxEntry.create("msg1", "type", {})
        await repo.save(entry)
        entry.mark_processed()
        await repo.update(entry)
        retrieved = await repo.get_by_id("msg1")
        assert retrieved is not None
        assert retrieved.status == InboxStatus.PROCESSED

    @pytest.mark.asyncio
    async def test_delete_processed(self):
        """delete_processed should remove old processed entries."""
        repo = InMemoryInboxRepository()
        entry = InboxEntry.create("msg1", "type", {})
        entry.mark_processed()
        entry.processed_at = datetime.utcnow() - timedelta(days=2)
        await repo.save(entry)
        deleted = await repo.delete_processed(datetime.utcnow() - timedelta(days=1))
        assert deleted == 1
        assert repo.count() == 0


class TestInboxService:
    """Tests for InboxService."""

    @pytest.mark.asyncio
    async def test_receive_new_message(self):
        """receive should accept new message."""
        repo = InMemoryInboxRepository()
        handler = MockMessageHandler()
        service = InboxService(repo, handler)
        is_new, entry = await service.receive("msg1", "type", {"key": "value"})
        assert is_new is True
        assert entry.message_id == "msg1"

    @pytest.mark.asyncio
    async def test_receive_duplicate_message(self):
        """receive should detect duplicate message."""
        repo = InMemoryInboxRepository()
        handler = MockMessageHandler()
        service = InboxService(repo, handler)
        await service.receive("msg1", "type", {"key": "value"})
        is_new, entry = await service.receive("msg1", "type", {"key": "value"})
        assert is_new is False

    @pytest.mark.asyncio
    async def test_process_success(self):
        """process should handle message successfully."""
        repo = InMemoryInboxRepository()
        handler = MockMessageHandler()
        service = InboxService(repo, handler)
        _, entry = await service.receive("msg1", "type", {"key": "value"})
        success = await service.process(entry)
        assert success is True
        assert len(handler.handled_messages) == 1

    @pytest.mark.asyncio
    async def test_process_failure(self):
        """process should handle failure."""
        repo = InMemoryInboxRepository()
        handler = MockMessageHandler(should_fail=True)
        service = InboxService(repo, handler)
        _, entry = await service.receive("msg1", "type", {"key": "value"})
        success = await service.process(entry)
        assert success is False
        retrieved = await repo.get_by_id("msg1")
        assert retrieved is not None
        assert retrieved.status == InboxStatus.FAILED

    @pytest.mark.asyncio
    async def test_receive_and_process(self):
        """receive_and_process should do both."""
        repo = InMemoryInboxRepository()
        handler = MockMessageHandler()
        service = InboxService(repo, handler)
        is_new, success = await service.receive_and_process(
            "msg1", "type", {"key": "value"}
        )
        assert is_new is True
        assert success is True

    @pytest.mark.asyncio
    async def test_is_duplicate(self):
        """is_duplicate should detect duplicates."""
        repo = InMemoryInboxRepository()
        handler = MockMessageHandler()
        service = InboxService(repo, handler)
        entry = InboxEntry.create("msg1", "type", {})
        await repo.save(entry)
        assert await service.is_duplicate(entry.idempotency_key or "") is True
        assert await service.is_duplicate("nonexistent") is False

    @pytest.mark.asyncio
    async def test_cleanup(self):
        """cleanup should remove old processed entries."""
        repo = InMemoryInboxRepository()
        handler = MockMessageHandler()
        service = InboxService(repo, handler)
        entry = InboxEntry.create("msg1", "type", {})
        entry.mark_processed()
        entry.processed_at = datetime.utcnow() - timedelta(days=10)
        await repo.save(entry)
        deleted = await service.cleanup(datetime.utcnow() - timedelta(days=7))
        assert deleted == 1
