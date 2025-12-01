"""Event Store implementations.

**Feature: code-review-refactoring, Task 1.6: Extract store module**
**Validates: Requirements 2.2**
"""

from abc import ABC, abstractmethod
from typing import Any

from .aggregate import Aggregate
from .events import EventStream, SourcedEvent
from .exceptions import ConcurrencyError
from .snapshots import Snapshot


class EventStore[AggregateT: Aggregate[Any], EventT: SourcedEvent](ABC):
    """Abstract event store interface.

    Event stores persist and retrieve event streams for aggregates.

    Type Parameters:
        AggregateT: The aggregate type this store handles.
        EventT: The event type this store handles.
    """

    @abstractmethod
    async def save(
        self,
        aggregate: AggregateT,
        expected_version: int | None = None,
    ) -> None:
        """Save uncommitted events from an aggregate.

        Args:
            aggregate: The aggregate with uncommitted events.
            expected_version: Expected version for optimistic concurrency.

        Raises:
            ConcurrencyError: If expected_version doesn't match.
        """
        ...

    @abstractmethod
    async def load(
        self,
        aggregate_id: str,
        aggregate_class: type[AggregateT],
    ) -> AggregateT | None:
        """Load an aggregate by replaying its events.

        Args:
            aggregate_id: The aggregate identifier.
            aggregate_class: The aggregate class to instantiate.

        Returns:
            The reconstructed aggregate or None if not found.
        """
        ...

    @abstractmethod
    async def get_events(
        self,
        aggregate_id: str,
        from_version: int = 0,
        to_version: int | None = None,
    ) -> list[EventT]:
        """Get events for an aggregate within a version range.

        Args:
            aggregate_id: The aggregate identifier.
            from_version: Start version (inclusive).
            to_version: End version (inclusive), None for all.

        Returns:
            List of events in the specified range.
        """
        ...

    @abstractmethod
    async def get_all_events(
        self,
        from_position: int = 0,
        limit: int = 100,
    ) -> list[EventT]:
        """Get all events across all aggregates.

        Useful for projections and read model updates.

        Args:
            from_position: Global position to start from.
            limit: Maximum number of events to return.

        Returns:
            List of events.
        """
        ...


class InMemoryEventStore[AggregateT: Aggregate[Any], EventT: SourcedEvent](EventStore[AggregateT, EventT]):
    """In-memory event store implementation.

    Useful for testing and development. Not suitable for production
    as events are lost on restart.
    """

    def __init__(self) -> None:
        """Initialize in-memory event store."""
        self._streams: dict[str, EventStream] = {}
        self._all_events: list[EventT] = []
        self._snapshots: dict[str, Snapshot[AggregateT]] = {}

    async def save(
        self,
        aggregate: AggregateT,
        expected_version: int | None = None,
    ) -> None:
        """Save uncommitted events from an aggregate."""
        aggregate_id = str(aggregate.id)
        events = aggregate.uncommitted_events

        if not events:
            return

        stream = self._streams.get(aggregate_id)
        if stream is None:
            stream = EventStream(
                aggregate_id=aggregate_id,
                aggregate_type=aggregate.__class__.__name__,
            )
            self._streams[aggregate_id] = stream

        if expected_version is not None and stream.version != expected_version:
            raise ConcurrencyError(
                "Optimistic concurrency check failed",
                expected_version=expected_version,
                actual_version=stream.version,
            )

        for event in events:
            stream.append(event)
            self._all_events.append(event)  # type: ignore[arg-type]

        aggregate.clear_uncommitted_events()

    async def load(
        self,
        aggregate_id: str,
        aggregate_class: type[AggregateT],
    ) -> AggregateT | None:
        """Load an aggregate by replaying its events."""
        stream = self._streams.get(aggregate_id)
        if stream is None:
            return None

        snapshot = self._snapshots.get(aggregate_id)
        from_version = 0

        aggregate = aggregate_class(aggregate_id)  # type: ignore[arg-type]

        if snapshot is not None:
            aggregate.load_from_snapshot(snapshot)
            from_version = snapshot.version

        events_to_replay = [e for e in stream.events if e.version > from_version]
        aggregate.load_from_history(events_to_replay)

        return aggregate

    async def get_events(
        self,
        aggregate_id: str,
        from_version: int = 0,
        to_version: int | None = None,
    ) -> list[EventT]:
        """Get events for an aggregate within a version range."""
        stream = self._streams.get(aggregate_id)
        if stream is None:
            return []

        events = stream.events
        if from_version > 0:
            events = [e for e in events if e.version >= from_version]
        if to_version is not None:
            events = [e for e in events if e.version <= to_version]

        return events  # type: ignore[return-value]

    async def get_all_events(
        self,
        from_position: int = 0,
        limit: int = 100,
    ) -> list[EventT]:
        """Get all events across all aggregates."""
        return self._all_events[from_position : from_position + limit]

    async def save_snapshot(self, aggregate: AggregateT) -> None:
        """Save a snapshot of the aggregate state.

        Args:
            aggregate: The aggregate to snapshot.
        """
        snapshot = Snapshot.from_aggregate(aggregate)
        self._snapshots[str(aggregate.id)] = snapshot  # type: ignore[assignment]

    async def get_snapshot(self, aggregate_id: str) -> Snapshot[AggregateT] | None:
        """Get the latest snapshot for an aggregate.

        Args:
            aggregate_id: The aggregate identifier.

        Returns:
            The snapshot or None if not found.
        """
        return self._snapshots.get(aggregate_id)

    def clear(self) -> None:
        """Clear all stored events and snapshots."""
        self._streams.clear()
        self._all_events.clear()
        self._snapshots.clear()
