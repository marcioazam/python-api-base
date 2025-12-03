"""Property-based tests for event sourcing.

**Feature: enterprise-features-2025, Tasks 2.2, 2.4, 2.5, 2.7**
**Validates: Requirements 2.1, 2.2, 2.3, 2.4**
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
import uuid

import pytest
from hypothesis import given, settings, strategies as st

from infrastructure.db.event_sourcing.aggregate import Aggregate
from infrastructure.db.event_sourcing.events import SourcedEvent
from infrastructure.db.event_sourcing.store import InMemoryEventStore
from infrastructure.db.event_sourcing.exceptions import ConcurrencyError


# Test event types
@dataclass(frozen=True, slots=True)
class TestEvent(SourcedEvent):
    """Test event for property testing."""

    data: str = ""


@dataclass(frozen=True, slots=True)
class CounterIncremented(SourcedEvent):
    """Event for counter increment."""

    amount: int = 1


@dataclass(frozen=True, slots=True)
class CounterDecremented(SourcedEvent):
    """Event for counter decrement."""

    amount: int = 1


# Test aggregate
class CounterAggregate(Aggregate[str]):
    """Test aggregate for property testing."""

    def __init__(self, id: str) -> None:
        super().__init__(id)
        self.count = 0

    def increment(self, amount: int = 1) -> None:
        """Increment the counter."""
        event = CounterIncremented(
            event_id=str(uuid.uuid4()),
            aggregate_id=str(self.id),
            version=0,
            timestamp=datetime.now(),
            metadata={},
            amount=amount,
        )
        self.raise_event(event)

    def decrement(self, amount: int = 1) -> None:
        """Decrement the counter."""
        event = CounterDecremented(
            event_id=str(uuid.uuid4()),
            aggregate_id=str(self.id),
            version=0,
            timestamp=datetime.now(),
            metadata={},
            amount=amount,
        )
        self.raise_event(event)

    def apply_event(self, event: SourcedEvent) -> None:
        """Apply event to update state."""
        if isinstance(event, CounterIncremented):
            self.count += event.amount
        elif isinstance(event, CounterDecremented):
            self.count -= event.amount


# Strategies
aggregate_ids = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N")),
    min_size=1,
    max_size=20,
)
amounts = st.integers(min_value=1, max_value=100)
operation_counts = st.integers(min_value=1, max_value=20)


class TestEventSourcingRoundTrip:
    """**Feature: enterprise-features-2025, Property 5: Event Sourcing Round-Trip**
    **Validates: Requirements 2.1, 2.2**
    """

    @given(aggregate_id=aggregate_ids, increments=st.lists(amounts, min_size=1, max_size=10))
    @settings(max_examples=50)
    def test_save_and_load_preserves_state(
        self, aggregate_id: str, increments: list[int]
    ) -> None:
        """For any aggregate, saving and loading preserves state."""

        async def run_test() -> None:
            store: InMemoryEventStore[CounterAggregate, SourcedEvent] = InMemoryEventStore()

            # Create and modify aggregate
            aggregate = CounterAggregate(aggregate_id)
            expected_count = 0
            for amount in increments:
                aggregate.increment(amount)
                expected_count += amount

            # Save
            await store.save(aggregate)

            # Load
            loaded = await store.load(aggregate_id, CounterAggregate)

            assert loaded is not None
            assert loaded.count == expected_count
            assert loaded.version == len(increments)

        asyncio.run(run_test())

    @given(aggregate_id=aggregate_ids, ops=st.lists(st.tuples(st.booleans(), amounts), min_size=1, max_size=15))
    @settings(max_examples=50)
    def test_mixed_operations_round_trip(
        self, aggregate_id: str, ops: list[tuple[bool, int]]
    ) -> None:
        """Mixed increment/decrement operations round-trip correctly."""

        async def run_test() -> None:
            store: InMemoryEventStore[CounterAggregate, SourcedEvent] = InMemoryEventStore()

            aggregate = CounterAggregate(aggregate_id)
            expected_count = 0
            for is_increment, amount in ops:
                if is_increment:
                    aggregate.increment(amount)
                    expected_count += amount
                else:
                    aggregate.decrement(amount)
                    expected_count -= amount

            await store.save(aggregate)
            loaded = await store.load(aggregate_id, CounterAggregate)

            assert loaded is not None
            assert loaded.count == expected_count

        asyncio.run(run_test())


class TestEventOrdering:
    """**Feature: enterprise-features-2025, Property 6: Event Ordering Preservation**
    **Validates: Requirements 2.2**
    """

    @given(aggregate_id=aggregate_ids, amounts=st.lists(amounts, min_size=2, max_size=10))
    @settings(max_examples=50)
    def test_events_applied_in_order(
        self, aggregate_id: str, amounts: list[int]
    ) -> None:
        """Events are replayed in the same order they were raised."""

        async def run_test() -> None:
            store: InMemoryEventStore[CounterAggregate, SourcedEvent] = InMemoryEventStore()

            aggregate = CounterAggregate(aggregate_id)
            for amount in amounts:
                aggregate.increment(amount)

            await store.save(aggregate)

            # Get events and verify ordering
            events = await store.get_events(aggregate_id)
            assert len(events) == len(amounts)

            for i, (event, expected_amount) in enumerate(zip(events, amounts)):
                assert event.version == i + 1
                assert isinstance(event, CounterIncremented)
                assert event.amount == expected_amount

        asyncio.run(run_test())


class TestOptimisticLocking:
    """**Feature: enterprise-features-2025, Property 7: Optimistic Locking Conflict Detection**
    **Validates: Requirements 2.3**
    """

    @given(aggregate_id=aggregate_ids, amount1=amounts, amount2=amounts)
    @settings(max_examples=50)
    def test_concurrent_modification_detected(
        self, aggregate_id: str, amount1: int, amount2: int
    ) -> None:
        """Concurrent modifications to same version are detected."""

        async def run_test() -> None:
            store: InMemoryEventStore[CounterAggregate, SourcedEvent] = InMemoryEventStore()

            # Create initial aggregate
            aggregate1 = CounterAggregate(aggregate_id)
            aggregate1.increment(amount1)
            await store.save(aggregate1)

            # Load two copies
            copy1 = await store.load(aggregate_id, CounterAggregate)
            copy2 = await store.load(aggregate_id, CounterAggregate)

            assert copy1 is not None
            assert copy2 is not None

            # Modify both
            copy1.increment(amount1)
            copy2.increment(amount2)

            # Save first copy with expected version
            await store.save(copy1, expected_version=1)

            # Second save should fail due to version mismatch
            with pytest.raises(ConcurrencyError):
                await store.save(copy2, expected_version=1)

        asyncio.run(run_test())

    @given(aggregate_id=aggregate_ids, amount=amounts)
    @settings(max_examples=30)
    def test_correct_version_succeeds(self, aggregate_id: str, amount: int) -> None:
        """Save with correct expected version succeeds."""

        async def run_test() -> None:
            store: InMemoryEventStore[CounterAggregate, SourcedEvent] = InMemoryEventStore()

            aggregate = CounterAggregate(aggregate_id)
            aggregate.increment(amount)
            await store.save(aggregate)

            loaded = await store.load(aggregate_id, CounterAggregate)
            assert loaded is not None

            loaded.increment(amount)
            # Should succeed with correct version
            await store.save(loaded, expected_version=1)

            final = await store.load(aggregate_id, CounterAggregate)
            assert final is not None
            assert final.version == 2

        asyncio.run(run_test())


class TestSnapshotConsistency:
    """**Feature: enterprise-features-2025, Property 8: Snapshot Consistency**
    **Validates: Requirements 2.4**
    """

    @given(
        aggregate_id=aggregate_ids,
        amounts=st.lists(amounts, min_size=3, max_size=10),
    )
    @settings(max_examples=30)
    def test_snapshot_replay_equals_full_replay(
        self, aggregate_id: str, amounts: list[int]
    ) -> None:
        """Replaying from snapshot produces same state as full replay."""

        async def run_test() -> None:
            store: InMemoryEventStore[CounterAggregate, SourcedEvent] = InMemoryEventStore()

            # Create aggregate with all events
            aggregate = CounterAggregate(aggregate_id)
            for amount in amounts:
                aggregate.increment(amount)
            await store.save(aggregate)

            # Save snapshot at current state
            await store.save_snapshot(aggregate)

            # Load - should use snapshot
            loaded = await store.load(aggregate_id, CounterAggregate)
            assert loaded is not None

            # State should match
            assert loaded.count == sum(amounts)
            assert loaded.version == len(amounts)

        asyncio.run(run_test())


class TestAggregateProperties:
    """Additional aggregate property tests."""

    @given(aggregate_id=aggregate_ids)
    @settings(max_examples=50)
    def test_new_aggregate_has_version_zero(self, aggregate_id: str) -> None:
        """New aggregates start at version 0."""
        aggregate = CounterAggregate(aggregate_id)
        assert aggregate.version == 0
        assert aggregate.count == 0
        assert len(aggregate.uncommitted_events) == 0

    @given(aggregate_id=aggregate_ids, amount=amounts)
    @settings(max_examples=50)
    def test_raising_event_increments_version(
        self, aggregate_id: str, amount: int
    ) -> None:
        """Raising an event increments the version."""
        aggregate = CounterAggregate(aggregate_id)
        initial_version = aggregate.version

        aggregate.increment(amount)

        assert aggregate.version == initial_version + 1
        assert len(aggregate.uncommitted_events) == 1

    @given(aggregate_id=aggregate_ids, amounts=st.lists(amounts, min_size=1, max_size=10))
    @settings(max_examples=50)
    def test_clear_uncommitted_events(
        self, aggregate_id: str, amounts: list[int]
    ) -> None:
        """Clearing uncommitted events empties the list."""
        aggregate = CounterAggregate(aggregate_id)
        for amount in amounts:
            aggregate.increment(amount)

        assert len(aggregate.uncommitted_events) == len(amounts)

        aggregate.clear_uncommitted_events()

        assert len(aggregate.uncommitted_events) == 0
        # Version should remain unchanged
        assert aggregate.version == len(amounts)
