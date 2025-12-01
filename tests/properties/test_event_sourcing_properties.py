"""Property tests for event_sourcing module.

**Feature: shared-modules-phase2**
**Validates: Requirements 5.1, 5.2, 6.1, 6.2, 6.3**
"""

import asyncio
from dataclasses import dataclass

import pytest
from hypothesis import given, settings, strategies as st

from my_app.infrastructure.db.event_sourcing import (
    Aggregate,
    ConcurrencyError,
    InMemoryEventStore,
    Snapshot,
    SourcedEvent,
)


@dataclass(frozen=True)
class TestEvent(SourcedEvent):
    """Test event for property tests."""

    value: str = ""


class TestAggregate(Aggregate[str]):
    """Test aggregate for property tests."""

    def __init__(self, id: str) -> None:
        super().__init__(id)
        self.values: list[str] = []

    def add_value(self, value: str) -> None:
        event = TestEvent(aggregate_id=str(self.id), value=value)
        self.raise_event(event)

    def apply_event(self, event: SourcedEvent) -> None:
        if isinstance(event, TestEvent):
            self.values.append(event.value)

    def to_snapshot_state(self) -> dict:
        return {"values": self.values.copy()}

    def restore_from_snapshot_state(self, state: dict) -> None:
        self.values = state.get("values", [])


class TestConcurrencyErrorMessageContent:
    """Property tests for ConcurrencyError message content.

    **Feature: shared-modules-phase2, Property 9: ConcurrencyError Message Content**
    **Validates: Requirements 5.2**
    """

    @settings(max_examples=100)
    @given(
        expected=st.integers(min_value=0, max_value=1000),
        actual=st.integers(min_value=0, max_value=1000),
    )
    def test_error_contains_versions(self, expected: int, actual: int) -> None:
        """Error message should contain expected and actual versions."""
        error = ConcurrencyError(
            "Test error",
            expected_version=expected,
            actual_version=actual,
        )
        msg = str(error)
        assert str(expected) in msg
        assert str(actual) in msg

    @settings(max_examples=100)
    @given(
        expected=st.integers(min_value=0, max_value=1000),
        actual=st.integers(min_value=0, max_value=1000),
    )
    def test_attributes_stored_correctly(self, expected: int, actual: int) -> None:
        """Attributes should be stored correctly."""
        error = ConcurrencyError(
            "Test error",
            expected_version=expected,
            actual_version=actual,
        )
        assert error.expected_version == expected
        assert error.actual_version == actual


class TestSnapshotHashIntegrity:
    """Property tests for snapshot hash integrity.

    **Feature: shared-modules-phase2, Property 10: Snapshot Hash Integrity**
    **Validates: Requirements 6.1**
    """

    @settings(max_examples=100)
    @given(
        values=st.lists(st.text(min_size=1, max_size=50), min_size=0, max_size=10)
    )
    def test_snapshot_hash_computed_correctly(self, values: list[str]) -> None:
        """Snapshot hash should match computed hash of state."""
        aggregate = TestAggregate("test-1")
        for value in values:
            aggregate.add_value(value)
        aggregate.clear_uncommitted_events()

        snapshot = Snapshot.from_aggregate(aggregate)

        # Hash should be non-empty
        assert snapshot.state_hash
        # Hash should validate
        assert snapshot.validate_hash()

    @settings(max_examples=100)
    @given(
        values=st.lists(st.text(min_size=1, max_size=50), min_size=1, max_size=10)
    )
    def test_corrupted_hash_detected(self, values: list[str]) -> None:
        """Corrupted hash should be detected."""
        aggregate = TestAggregate("test-1")
        for value in values:
            aggregate.add_value(value)
        aggregate.clear_uncommitted_events()

        snapshot = Snapshot.from_aggregate(aggregate)

        # Corrupt the hash
        snapshot.state_hash = "corrupted_hash_value"

        # Validation should fail
        assert not snapshot.validate_hash()


class TestEventStoreOptimisticLocking:
    """Property tests for event store optimistic locking.

    **Feature: shared-modules-phase2, Property 8: Event Store Optimistic Locking**
    **Validates: Requirements 5.1**
    """

    @pytest.mark.asyncio
    async def test_concurrent_saves_raise_concurrency_error(self) -> None:
        """Concurrent saves should raise ConcurrencyError."""
        store = InMemoryEventStore[TestAggregate, TestEvent]()

        # Create and save initial aggregate
        agg1 = TestAggregate("test-1")
        agg1.add_value("initial")
        await store.save(agg1)

        # Load two copies
        loaded1 = await store.load("test-1", TestAggregate)
        loaded2 = await store.load("test-1", TestAggregate)

        assert loaded1 is not None
        assert loaded2 is not None

        # Modify both
        loaded1.add_value("change1")
        loaded2.add_value("change2")

        # Save first one with expected version
        await store.save(loaded1, expected_version=1)

        # Second save should fail
        with pytest.raises(ConcurrencyError) as exc_info:
            await store.save(loaded2, expected_version=1)

        # Error should contain version info
        assert exc_info.value.expected_version == 1
        assert exc_info.value.actual_version == 2


class TestSnapshotValidationFallback:
    """Property tests for snapshot validation with fallback.

    **Feature: shared-modules-phase2, Property 11: Snapshot Validation Detection**
    **Validates: Requirements 6.2, 6.3**
    """

    @pytest.mark.asyncio
    async def test_valid_snapshot_used(self) -> None:
        """Valid snapshot should be used for loading."""
        store = InMemoryEventStore[TestAggregate, TestEvent]()

        # Create aggregate with events
        agg = TestAggregate("test-1")
        agg.add_value("value1")
        agg.add_value("value2")
        await store.save(agg)

        # Save snapshot
        await store.save_snapshot(agg)

        # Load should use snapshot
        loaded = await store.load("test-1", TestAggregate)
        assert loaded is not None
        assert loaded.values == ["value1", "value2"]
