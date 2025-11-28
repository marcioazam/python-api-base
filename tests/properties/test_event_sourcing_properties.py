"""Property-based tests for Event Sourcing pattern.

**Feature: api-architecture-analysis, Property Tests for Task 3.4**
**Validates: Requirements 9.5**
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import pytest
from hypothesis import given, settings, strategies as st

from my_api.shared.event_sourcing import (
    Aggregate,
    ConcurrencyError,
    EventSourcedRepository,
    EventStream,
    InMemoryEventStore,
    InMemoryProjection,
    Snapshot,
    SourcedEvent,
)


# =============================================================================
# Test Domain Events
# =============================================================================


@dataclass(frozen=True, slots=True)
class CounterIncremented(SourcedEvent):
    """Event for counter increment."""

    amount: int = 1


@dataclass(frozen=True, slots=True)
class CounterDecremented(SourcedEvent):
    """Event for counter decrement."""

    amount: int = 1


@dataclass(frozen=True, slots=True)
class CounterReset(SourcedEvent):
    """Event for counter reset."""

    pass


# =============================================================================
# Test Aggregate
# =============================================================================


class Counter(Aggregate[str]):
    """Simple counter aggregate for testing."""

    def __init__(self, id: str) -> None:
        super().__init__(id)
        self.value: int = 0
        self.operations: int = 0

    def apply_event(self, event: SourcedEvent) -> None:
        """Apply event to update state."""
        if isinstance(event, CounterIncremented):
            self.value += event.amount
            self.operations += 1
        elif isinstance(event, CounterDecremented):
            self.value -= event.amount
            self.operations += 1
        elif isinstance(event, CounterReset):
            self.value = 0
            self.operations += 1

    def increment(self, amount: int = 1) -> None:
        """Increment the counter."""
        if amount <= 0:
            raise ValueError("Amount must be positive")
        self.raise_event(CounterIncremented(aggregate_id=self.id, amount=amount))

    def decrement(self, amount: int = 1) -> None:
        """Decrement the counter."""
        if amount <= 0:
            raise ValueError("Amount must be positive")
        self.raise_event(CounterDecremented(aggregate_id=self.id, amount=amount))

    def reset(self) -> None:
        """Reset the counter to zero."""
        self.raise_event(CounterReset(aggregate_id=self.id))


# =============================================================================
# Test Projection
# =============================================================================


class CounterSummaryProjection(InMemoryProjection[SourcedEvent]):
    """Projection that tracks counter summaries."""

    async def apply(self, event: SourcedEvent) -> None:
        """Apply event to projection."""
        aggregate_id = event.aggregate_id

        if aggregate_id not in self._state:
            self._state[aggregate_id] = {
                "total_increments": 0,
                "total_decrements": 0,
                "total_resets": 0,
            }

        if isinstance(event, CounterIncremented):
            self._state[aggregate_id]["total_increments"] += event.amount
        elif isinstance(event, CounterDecremented):
            self._state[aggregate_id]["total_decrements"] += event.amount
        elif isinstance(event, CounterReset):
            self._state[aggregate_id]["total_resets"] += 1


# =============================================================================
# Strategies
# =============================================================================


@st.composite
def operation_sequence(draw: st.DrawFn) -> list[tuple[str, int]]:
    """Generate a sequence of counter operations."""
    ops = draw(
        st.lists(
            st.tuples(
                st.sampled_from(["increment", "decrement", "reset"]),
                st.integers(min_value=1, max_value=100),
            ),
            min_size=1,
            max_size=20,
        )
    )
    return ops


# =============================================================================
# Property Tests
# =============================================================================


class TestEventSourcingProperties:
    """Property-based tests for event sourcing."""

    @given(st.text(min_size=1, max_size=50))
    @settings(max_examples=100)
    def test_event_has_unique_id(self, aggregate_id: str) -> None:
        """Property: Each event has a unique event_id.

        **Feature: api-architecture-analysis, Property: Event uniqueness**
        **Validates: Requirements 9.5**
        """
        event1 = CounterIncremented(aggregate_id=aggregate_id, amount=1)
        event2 = CounterIncremented(aggregate_id=aggregate_id, amount=1)

        assert event1.event_id != event2.event_id

    @given(st.text(min_size=1, max_size=50))
    @settings(max_examples=100)
    def test_event_type_matches_class_name(self, aggregate_id: str) -> None:
        """Property: Event type equals class name.

        **Feature: api-architecture-analysis, Property: Event type consistency**
        **Validates: Requirements 9.5**
        """
        event = CounterIncremented(aggregate_id=aggregate_id, amount=5)
        assert event.event_type == "CounterIncremented"

    @given(operation_sequence())
    @settings(max_examples=100)
    def test_aggregate_version_equals_event_count(
        self, operations: list[tuple[str, int]]
    ) -> None:
        """Property: Aggregate version equals number of applied events.

        **Feature: api-architecture-analysis, Property: Version consistency**
        **Validates: Requirements 9.5**
        """
        counter = Counter("test-counter")

        for op, amount in operations:
            if op == "increment":
                counter.increment(amount)
            elif op == "decrement":
                counter.decrement(amount)
            else:
                counter.reset()

        assert counter.version == len(operations)
        assert len(counter.uncommitted_events) == len(operations)

    @given(operation_sequence())
    @settings(max_examples=100)
    def test_replay_produces_same_state(
        self, operations: list[tuple[str, int]]
    ) -> None:
        """Property: Replaying events produces identical state.

        **Feature: api-architecture-analysis, Property: Event replay determinism**
        **Validates: Requirements 9.5**
        """
        # Create and apply operations
        counter1 = Counter("test-counter")
        for op, amount in operations:
            if op == "increment":
                counter1.increment(amount)
            elif op == "decrement":
                counter1.decrement(amount)
            else:
                counter1.reset()

        # Replay events on new aggregate
        counter2 = Counter("test-counter")
        counter2.load_from_history(counter1.uncommitted_events)

        assert counter2.value == counter1.value
        assert counter2.operations == counter1.operations
        assert counter2.version == counter1.version

    @given(operation_sequence())
    @settings(max_examples=100)
    def test_snapshot_preserves_state(
        self, operations: list[tuple[str, int]]
    ) -> None:
        """Property: Snapshot and restore preserves aggregate state.

        **Feature: api-architecture-analysis, Property: Snapshot consistency**
        **Validates: Requirements 9.5**
        """
        counter1 = Counter("test-counter")
        for op, amount in operations:
            if op == "increment":
                counter1.increment(amount)
            elif op == "decrement":
                counter1.decrement(amount)
            else:
                counter1.reset()

        # Create snapshot
        snapshot = Snapshot.from_aggregate(counter1)

        # Restore from snapshot
        counter2 = Counter("test-counter")
        counter2.load_from_snapshot(snapshot)

        assert counter2.value == counter1.value
        assert counter2.operations == counter1.operations
        assert counter2.version == counter1.version


class TestEventStreamProperties:
    """Property-based tests for event streams."""

    @given(st.lists(st.integers(min_value=1, max_value=100), min_size=1, max_size=20))
    @settings(max_examples=100)
    def test_stream_version_equals_event_count(self, amounts: list[int]) -> None:
        """Property: Stream version equals number of events.

        **Feature: api-architecture-analysis, Property: Stream version**
        **Validates: Requirements 9.5**
        """
        stream = EventStream(
            aggregate_id="test",
            aggregate_type="Counter",
        )

        for i, amount in enumerate(amounts):
            event = CounterIncremented(
                aggregate_id="test",
                version=i + 1,
                amount=amount,
            )
            stream.append(event)

        assert stream.version == len(amounts)
        assert len(stream.events) == len(amounts)


@pytest.mark.asyncio
class TestInMemoryEventStoreProperties:
    """Property-based tests for in-memory event store."""

    @given(operation_sequence())
    @settings(max_examples=100)
    async def test_save_and_load_round_trip(
        self, operations: list[tuple[str, int]]
    ) -> None:
        """Property: Save then load returns equivalent aggregate.

        **Feature: api-architecture-analysis, Property: Store round-trip**
        **Validates: Requirements 9.5**
        """
        store = InMemoryEventStore[Counter, SourcedEvent]()

        # Create and save
        counter1 = Counter("test-counter")
        for op, amount in operations:
            if op == "increment":
                counter1.increment(amount)
            elif op == "decrement":
                counter1.decrement(amount)
            else:
                counter1.reset()

        await store.save(counter1)

        # Load and compare
        counter2 = await store.load("test-counter", Counter)

        assert counter2 is not None
        assert counter2.value == counter1.value
        assert counter2.operations == counter1.operations
        assert counter2.version == counter1.version

    @given(operation_sequence())
    @settings(max_examples=100)
    async def test_get_events_returns_all_events(
        self, operations: list[tuple[str, int]]
    ) -> None:
        """Property: get_events returns all saved events.

        **Feature: api-architecture-analysis, Property: Event retrieval**
        **Validates: Requirements 9.5**
        """
        store = InMemoryEventStore[Counter, SourcedEvent]()

        counter = Counter("test-counter")
        for op, amount in operations:
            if op == "increment":
                counter.increment(amount)
            elif op == "decrement":
                counter.decrement(amount)
            else:
                counter.reset()

        await store.save(counter)

        events = await store.get_events("test-counter")
        assert len(events) == len(operations)

    @given(st.integers(min_value=1, max_value=10))
    @settings(max_examples=50)
    async def test_concurrency_check_fails_on_version_mismatch(
        self, num_ops: int
    ) -> None:
        """Property: Optimistic concurrency check fails on version mismatch.

        **Feature: api-architecture-analysis, Property: Concurrency control**
        **Validates: Requirements 9.5**
        """
        store = InMemoryEventStore[Counter, SourcedEvent]()

        # Create and save initial state
        counter = Counter("test-counter")
        for _ in range(num_ops):
            counter.increment(1)
        await store.save(counter)

        # Load and modify
        loaded = await store.load("test-counter", Counter)
        assert loaded is not None
        loaded.increment(1)

        # Try to save with wrong expected version
        with pytest.raises(ConcurrencyError):
            await store.save(loaded, expected_version=0)

    @given(operation_sequence())
    @settings(max_examples=100)
    async def test_snapshot_speeds_up_loading(
        self, operations: list[tuple[str, int]]
    ) -> None:
        """Property: Loading with snapshot produces same state.

        **Feature: api-architecture-analysis, Property: Snapshot loading**
        **Validates: Requirements 9.5**
        """
        store = InMemoryEventStore[Counter, SourcedEvent]()

        # Create and save with snapshot
        counter1 = Counter("test-counter")
        for op, amount in operations:
            if op == "increment":
                counter1.increment(amount)
            elif op == "decrement":
                counter1.decrement(amount)
            else:
                counter1.reset()

        await store.save(counter1)
        await store.save_snapshot(counter1)

        # Add more events after snapshot
        counter1.increment(10)
        await store.save(counter1)

        # Load (should use snapshot + remaining events)
        counter2 = await store.load("test-counter", Counter)

        assert counter2 is not None
        assert counter2.value == counter1.value
        assert counter2.version == counter1.version


@pytest.mark.asyncio
class TestProjectionProperties:
    """Property-based tests for projections."""

    @given(operation_sequence())
    @settings(max_examples=100)
    async def test_projection_tracks_all_operations(
        self, operations: list[tuple[str, int]]
    ) -> None:
        """Property: Projection correctly tracks all operations.

        **Feature: api-architecture-analysis, Property: Projection accuracy**
        **Validates: Requirements 9.5**
        """
        projection = CounterSummaryProjection()

        counter = Counter("test-counter")
        events = []

        for op, amount in operations:
            if op == "increment":
                counter.increment(amount)
            elif op == "decrement":
                counter.decrement(amount)
            else:
                counter.reset()

        # Apply events to projection
        for event in counter.uncommitted_events:
            await projection.apply(event)

        # Calculate expected values
        expected_increments = sum(
            amount for op, amount in operations if op == "increment"
        )
        expected_decrements = sum(
            amount for op, amount in operations if op == "decrement"
        )
        expected_resets = sum(1 for op, _ in operations if op == "reset")

        state = projection.state.get("test-counter", {})
        assert state.get("total_increments", 0) == expected_increments
        assert state.get("total_decrements", 0) == expected_decrements
        assert state.get("total_resets", 0) == expected_resets

    @given(operation_sequence())
    @settings(max_examples=100)
    async def test_projection_rebuild_produces_same_state(
        self, operations: list[tuple[str, int]]
    ) -> None:
        """Property: Rebuilding projection produces same state.

        **Feature: api-architecture-analysis, Property: Projection rebuild**
        **Validates: Requirements 9.5**
        """
        counter = Counter("test-counter")
        for op, amount in operations:
            if op == "increment":
                counter.increment(amount)
            elif op == "decrement":
                counter.decrement(amount)
            else:
                counter.reset()

        events = counter.uncommitted_events

        # Build projection incrementally
        projection1 = CounterSummaryProjection()
        for event in events:
            await projection1.apply(event)

        # Rebuild projection from scratch
        projection2 = CounterSummaryProjection()
        await projection2.rebuild(events)

        assert projection1.state == projection2.state


@pytest.mark.asyncio
class TestEventSourcedRepositoryProperties:
    """Property-based tests for event-sourced repository."""

    @given(operation_sequence())
    @settings(max_examples=100)
    async def test_repository_save_and_get(
        self, operations: list[tuple[str, int]]
    ) -> None:
        """Property: Repository save and get returns equivalent aggregate.

        **Feature: api-architecture-analysis, Property: Repository round-trip**
        **Validates: Requirements 9.5**
        """
        store = InMemoryEventStore[Counter, SourcedEvent]()
        repo = EventSourcedRepository(store, Counter, snapshot_frequency=5)

        counter1 = Counter("test-counter")
        for op, amount in operations:
            if op == "increment":
                counter1.increment(amount)
            elif op == "decrement":
                counter1.decrement(amount)
            else:
                counter1.reset()

        await repo.save(counter1)

        counter2 = await repo.get_by_id("test-counter")

        assert counter2 is not None
        assert counter2.value == counter1.value
        assert counter2.version == counter1.version

    @given(st.text(min_size=1, max_size=50))
    @settings(max_examples=100)
    async def test_repository_exists_returns_correct_value(
        self, aggregate_id: str
    ) -> None:
        """Property: exists() returns correct boolean.

        **Feature: api-architecture-analysis, Property: Repository exists**
        **Validates: Requirements 9.5**
        """
        store = InMemoryEventStore[Counter, SourcedEvent]()
        repo = EventSourcedRepository(store, Counter)

        # Should not exist initially
        assert not await repo.exists(aggregate_id)

        # Create and save
        counter = Counter(aggregate_id)
        counter.increment(1)
        await repo.save(counter)

        # Should exist now
        assert await repo.exists(aggregate_id)



# =============================================================================
# Backward Compatibility Tests (Post-Refactoring)
# =============================================================================


class TestBackwardCompatibilityProperties:
    """Property tests for backward compatibility after refactoring.

    **Feature: code-review-refactoring, Property 1: Backward Compatibility**
    **Validates: Requirements 1.2, 1.4**
    """

    @given(st.text(min_size=1, max_size=50))
    @settings(max_examples=100)
    def test_all_public_symbols_importable(self, _: str) -> None:
        """Property: All original public symbols are importable.

        **Feature: code-review-refactoring, Property 1: Backward Compatibility**
        **Validates: Requirements 1.2, 1.4**
        """
        # Import all symbols that were available before refactoring
        from my_api.shared.event_sourcing import (
            Aggregate,
            AggregateId,
            AggregateT,
            ConcurrencyError,
            EventSourcedRepository,
            EventStore,
            EventStream,
            EventT,
            InMemoryEventStore,
            InMemoryProjection,
            Projection,
            Snapshot,
            SourcedEvent,
        )

        # Verify they are the correct types
        assert Aggregate is not None
        assert SourcedEvent is not None
        assert EventStore is not None
        assert InMemoryEventStore is not None
        assert EventStream is not None
        assert Snapshot is not None
        assert Projection is not None
        assert InMemoryProjection is not None
        assert EventSourcedRepository is not None
        assert ConcurrencyError is not None

    @given(st.text(min_size=1, max_size=50))
    @settings(max_examples=100)
    def test_sourced_event_creation_unchanged(self, aggregate_id: str) -> None:
        """Property: SourcedEvent creation behavior unchanged.

        **Feature: code-review-refactoring, Property 1: Backward Compatibility**
        **Validates: Requirements 1.2, 1.4**
        """
        from my_api.shared.event_sourcing import SourcedEvent

        event = SourcedEvent(aggregate_id=aggregate_id)

        assert event.aggregate_id == aggregate_id
        assert event.version == 0
        assert event.event_id is not None
        assert event.timestamp is not None
        assert event.event_type == "SourcedEvent"

    @given(st.text(min_size=1, max_size=50))
    @settings(max_examples=100)
    def test_event_stream_behavior_unchanged(self, aggregate_id: str) -> None:
        """Property: EventStream behavior unchanged after refactoring.

        **Feature: code-review-refactoring, Property 1: Backward Compatibility**
        **Validates: Requirements 1.2, 1.4**
        """
        from my_api.shared.event_sourcing import EventStream, SourcedEvent

        stream = EventStream(
            aggregate_id=aggregate_id,
            aggregate_type="TestAggregate",
        )

        assert stream.version == 0
        assert len(stream.events) == 0

        event = SourcedEvent(aggregate_id=aggregate_id, version=1)
        stream.append(event)

        assert stream.version == 1
        assert len(stream.events) == 1

    @given(st.text(min_size=1, max_size=50))
    @settings(max_examples=100)
    def test_concurrency_error_is_exception(self, message: str) -> None:
        """Property: ConcurrencyError is still an Exception.

        **Feature: code-review-refactoring, Property 1: Backward Compatibility**
        **Validates: Requirements 1.2, 1.4**
        """
        from my_api.shared.event_sourcing import ConcurrencyError

        error = ConcurrencyError(message)

        assert isinstance(error, Exception)
        assert str(error) == message


@pytest.mark.asyncio
class TestRoundTripProperties:
    """Property tests for event sourcing round-trip after refactoring.

    **Feature: code-review-refactoring, Property 2: Event Sourcing Round-Trip**
    **Validates: Requirements 2.5, 12.1**
    """

    @given(operation_sequence())
    @settings(max_examples=100)
    async def test_save_load_round_trip_preserves_state(
        self, operations: list[tuple[str, int]]
    ) -> None:
        """Property: Save then load produces equivalent aggregate state.

        **Feature: code-review-refactoring, Property 2: Event Sourcing Round-Trip**
        **Validates: Requirements 2.5, 12.1**
        """
        from my_api.shared.event_sourcing import InMemoryEventStore, SourcedEvent

        store = InMemoryEventStore[Counter, SourcedEvent]()

        # Create aggregate and apply operations
        original = Counter("round-trip-test")
        for op, amount in operations:
            if op == "increment":
                original.increment(amount)
            elif op == "decrement":
                original.decrement(amount)
            else:
                original.reset()

        # Save to store
        await store.save(original)

        # Load from store
        loaded = await store.load("round-trip-test", Counter)

        # Verify round-trip preserves state
        assert loaded is not None
        assert loaded.id == original.id
        assert loaded.value == original.value
        assert loaded.version == original.version
        assert loaded.operations == original.operations

    @given(operation_sequence())
    @settings(max_examples=100)
    async def test_snapshot_round_trip_preserves_state(
        self, operations: list[tuple[str, int]]
    ) -> None:
        """Property: Snapshot then restore produces equivalent state.

        **Feature: code-review-refactoring, Property 2: Event Sourcing Round-Trip**
        **Validates: Requirements 2.5, 12.1**
        """
        from my_api.shared.event_sourcing import Snapshot

        # Create aggregate and apply operations
        original = Counter("snapshot-test")
        for op, amount in operations:
            if op == "increment":
                original.increment(amount)
            elif op == "decrement":
                original.decrement(amount)
            else:
                original.reset()

        # Create snapshot
        snapshot = Snapshot.from_aggregate(original)

        # Restore to new aggregate
        restored = Counter("snapshot-test")
        restored.load_from_snapshot(snapshot)

        # Verify snapshot round-trip preserves state
        assert restored.value == original.value
        assert restored.version == original.version
        assert restored.operations == original.operations
