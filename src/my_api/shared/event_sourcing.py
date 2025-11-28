"""Event Sourcing pattern implementation.

Provides generic event store, aggregate base class, and event replay
capabilities for building event-sourced systems.

**Feature: api-architecture-analysis, Task 3.4: Event Sourcing Pattern**
**Validates: Requirements 9.5**

Usage:
    from my_api.shared.event_sourcing import (
        Aggregate,
        EventStore,
        InMemoryEventStore,
        SourcedEvent,
    )

    # Define domain events
    @dataclass(frozen=True)
    class OrderCreated(SourcedEvent):
        order_id: str
        customer_id: str
        total: float

    @dataclass(frozen=True)
    class OrderShipped(SourcedEvent):
        order_id: str
        tracking_number: str

    # Define aggregate
    class Order(Aggregate[str]):
        def __init__(self, id: str) -> None:
            super().__init__(id)
            self.customer_id: str = ""
            self.total: float = 0.0
            self.status: str = "pending"
            self.tracking_number: str | None = None

        def apply_event(self, event: SourcedEvent) -> None:
            if isinstance(event, OrderCreated):
                self.customer_id = event.customer_id
                self.total = event.total
            elif isinstance(event, OrderShipped):
                self.status = "shipped"
                self.tracking_number = event.tracking_number

        # Command methods
        def create(self, customer_id: str, total: float) -> None:
            self.raise_event(OrderCreated(
                aggregate_id=self.id,
                order_id=self.id,
                customer_id=customer_id,
                total=total,
            ))

        def ship(self, tracking_number: str) -> None:
            if self.status != "pending":
                raise ValueError("Order already shipped")
            self.raise_event(OrderShipped(
                aggregate_id=self.id,
                order_id=self.id,
                tracking_number=tracking_number,
            ))

    # Use event store
    store = InMemoryEventStore[Order, SourcedEvent]()
    
    order = Order("order-123")
    order.create("customer-456", 99.99)
    order.ship("TRACK-789")
    
    await store.save(order)
    
    # Replay from events
    loaded_order = await store.load("order-123", Order)
"""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Generic, TypeVar
from uuid import uuid4

from pydantic import BaseModel

# Type variables
AggregateId = TypeVar("AggregateId", str, int)
EventT = TypeVar("EventT", bound="SourcedEvent")
AggregateT = TypeVar("AggregateT", bound="Aggregate[Any]")


@dataclass(frozen=True, slots=True)
class SourcedEvent:
    """Base class for event-sourced events.

    All events in an event-sourced system should inherit from this class.
    Events are immutable records of state changes.
    """

    event_id: str = field(default_factory=lambda: str(uuid4()))
    aggregate_id: str = ""
    version: int = 0
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(tz=timezone.utc)
    )
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def event_type(self) -> str:
        """Return the event type name."""
        return self.__class__.__name__


@dataclass
class EventStream:
    """Represents a stream of events for an aggregate.

    Contains all events for a specific aggregate instance,
    along with metadata about the stream.
    """

    aggregate_id: str
    aggregate_type: str
    events: list[SourcedEvent] = field(default_factory=list)
    version: int = 0
    created_at: datetime = field(
        default_factory=lambda: datetime.now(tz=timezone.utc)
    )
    updated_at: datetime = field(
        default_factory=lambda: datetime.now(tz=timezone.utc)
    )

    def append(self, event: SourcedEvent) -> None:
        """Append an event to the stream."""
        self.events.append(event)
        self.version = len(self.events)
        self.updated_at = datetime.now(tz=timezone.utc)


@dataclass
class Snapshot(Generic[AggregateT]):
    """Snapshot of aggregate state for performance optimization.

    Snapshots allow faster aggregate reconstruction by storing
    periodic state snapshots instead of replaying all events.
    """

    aggregate_id: str
    aggregate_type: str
    version: int
    state: dict[str, Any]
    created_at: datetime = field(
        default_factory=lambda: datetime.now(tz=timezone.utc)
    )

    @classmethod
    def from_aggregate(cls, aggregate: "Aggregate[Any]") -> "Snapshot[Any]":
        """Create a snapshot from an aggregate instance."""
        return cls(
            aggregate_id=str(aggregate.id),
            aggregate_type=aggregate.__class__.__name__,
            version=aggregate.version,
            state=aggregate.to_snapshot_state(),
        )


class Aggregate(ABC, Generic[AggregateId]):
    """Base class for event-sourced aggregates.

    Aggregates are the consistency boundaries in event sourcing.
    They encapsulate state and behavior, and all state changes
    are recorded as events.

    Type Parameters:
        AggregateId: The type of the aggregate identifier.
    """

    def __init__(self, id: AggregateId) -> None:
        """Initialize aggregate.

        Args:
            id: Unique identifier for this aggregate.
        """
        self._id = id
        self._version = 0
        self._uncommitted_events: list[SourcedEvent] = []

    @property
    def id(self) -> AggregateId:
        """Get the aggregate identifier."""
        return self._id

    @property
    def version(self) -> int:
        """Get the current version (number of applied events)."""
        return self._version

    @property
    def uncommitted_events(self) -> list[SourcedEvent]:
        """Get events that haven't been persisted yet."""
        return self._uncommitted_events.copy()

    def clear_uncommitted_events(self) -> None:
        """Clear the list of uncommitted events after persistence."""
        self._uncommitted_events.clear()

    def raise_event(self, event: SourcedEvent) -> None:
        """Raise a new event and apply it to the aggregate.

        This method should be called from command methods to
        record state changes.

        Args:
            event: The event to raise.
        """
        # Create event with correct version
        versioned_event = self._create_versioned_event(event)
        self._apply_and_track(versioned_event)

    def _create_versioned_event(self, event: SourcedEvent) -> SourcedEvent:
        """Create a new event instance with the correct version."""
        from dataclasses import fields
        
        # Get all field values from the event using dataclass fields
        base_fields = {"event_id", "aggregate_id", "version", "timestamp", "metadata"}
        extra_kwargs = {}
        
        for f in fields(event):
            if f.name not in base_fields:
                extra_kwargs[f.name] = getattr(event, f.name)
        
        # Create new instance with updated version
        return type(event)(
            event_id=event.event_id,
            aggregate_id=str(self._id),
            version=self._version + 1,
            timestamp=event.timestamp,
            metadata=event.metadata,
            **extra_kwargs,
        )

    def _apply_and_track(self, event: SourcedEvent) -> None:
        """Apply event and track it as uncommitted."""
        self.apply_event(event)
        self._version = event.version
        self._uncommitted_events.append(event)

    @abstractmethod
    def apply_event(self, event: SourcedEvent) -> None:
        """Apply an event to update aggregate state.

        This method should update the aggregate's internal state
        based on the event. It must be deterministic and side-effect free.

        Args:
            event: The event to apply.
        """
        ...

    def load_from_history(self, events: Sequence[SourcedEvent]) -> None:
        """Reconstruct aggregate state from event history.

        Args:
            events: Historical events to replay.
        """
        for event in events:
            self.apply_event(event)
            self._version = event.version

    def load_from_snapshot(self, snapshot: Snapshot[Any]) -> None:
        """Restore aggregate state from a snapshot.

        Args:
            snapshot: The snapshot to restore from.
        """
        self._version = snapshot.version
        self.restore_from_snapshot_state(snapshot.state)

    def to_snapshot_state(self) -> dict[str, Any]:
        """Convert aggregate state to a dictionary for snapshotting.

        Override this method to customize snapshot serialization.

        Returns:
            Dictionary representation of aggregate state.
        """
        return {
            k: v
            for k, v in self.__dict__.items()
            if not k.startswith("_")
        }

    def restore_from_snapshot_state(self, state: dict[str, Any]) -> None:
        """Restore aggregate state from a snapshot dictionary.

        Override this method to customize snapshot deserialization.

        Args:
            state: Dictionary representation of aggregate state.
        """
        for key, value in state.items():
            if hasattr(self, key):
                setattr(self, key, value)


class EventStore(ABC, Generic[AggregateT, EventT]):
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


class InMemoryEventStore(EventStore[AggregateT, EventT]):
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

        # Get or create stream
        stream = self._streams.get(aggregate_id)
        if stream is None:
            stream = EventStream(
                aggregate_id=aggregate_id,
                aggregate_type=aggregate.__class__.__name__,
            )
            self._streams[aggregate_id] = stream

        # Optimistic concurrency check
        if expected_version is not None and stream.version != expected_version:
            raise ConcurrencyError(
                f"Expected version {expected_version}, but found {stream.version}"
            )

        # Append events
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

        # Check for snapshot
        snapshot = self._snapshots.get(aggregate_id)
        from_version = 0

        aggregate = aggregate_class(aggregate_id)  # type: ignore[arg-type]

        if snapshot is not None:
            aggregate.load_from_snapshot(snapshot)
            from_version = snapshot.version

        # Replay events after snapshot
        events_to_replay = [
            e for e in stream.events if e.version > from_version
        ]
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

    async def get_snapshot(
        self, aggregate_id: str
    ) -> Snapshot[AggregateT] | None:
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


class ConcurrencyError(Exception):
    """Raised when optimistic concurrency check fails."""

    pass


# =============================================================================
# Event Projections
# =============================================================================


class Projection(ABC, Generic[EventT]):
    """Base class for event projections.

    Projections build read models from event streams.
    They subscribe to events and update their internal state.
    """

    @abstractmethod
    async def apply(self, event: EventT) -> None:
        """Apply an event to update the projection.

        Args:
            event: The event to apply.
        """
        ...

    @abstractmethod
    async def rebuild(self, events: Sequence[EventT]) -> None:
        """Rebuild the projection from a sequence of events.

        Args:
            events: All events to replay.
        """
        ...


class InMemoryProjection(Projection[EventT], Generic[EventT]):
    """In-memory projection with dictionary-based state."""

    def __init__(self) -> None:
        """Initialize projection."""
        self._state: dict[str, Any] = {}
        self._position: int = 0

    @property
    def state(self) -> dict[str, Any]:
        """Get the current projection state."""
        return self._state.copy()

    @property
    def position(self) -> int:
        """Get the last processed event position."""
        return self._position

    async def rebuild(self, events: Sequence[EventT]) -> None:
        """Rebuild the projection from events."""
        self._state.clear()
        self._position = 0
        for event in events:
            await self.apply(event)
            self._position += 1


# =============================================================================
# Event Store Repository Adapter
# =============================================================================


class EventSourcedRepository(Generic[AggregateT, EventT]):
    """Repository adapter for event-sourced aggregates.

    Provides a familiar repository interface while using
    event sourcing under the hood.
    """

    def __init__(
        self,
        event_store: EventStore[AggregateT, EventT],
        aggregate_class: type[AggregateT],
        snapshot_frequency: int = 100,
    ) -> None:
        """Initialize repository.

        Args:
            event_store: The underlying event store.
            aggregate_class: The aggregate class to work with.
            snapshot_frequency: Create snapshot every N events.
        """
        self._store = event_store
        self._aggregate_class = aggregate_class
        self._snapshot_frequency = snapshot_frequency

    async def get_by_id(self, id: str) -> AggregateT | None:
        """Get an aggregate by ID.

        Args:
            id: The aggregate identifier.

        Returns:
            The aggregate or None if not found.
        """
        return await self._store.load(id, self._aggregate_class)

    async def save(
        self,
        aggregate: AggregateT,
        expected_version: int | None = None,
    ) -> None:
        """Save an aggregate.

        Args:
            aggregate: The aggregate to save.
            expected_version: Expected version for optimistic concurrency.
        """
        await self._store.save(aggregate, expected_version)

        # Create snapshot if needed
        if (
            self._snapshot_frequency > 0
            and aggregate.version % self._snapshot_frequency == 0
            and hasattr(self._store, "save_snapshot")
        ):
            await self._store.save_snapshot(aggregate)  # type: ignore[attr-defined]

    async def exists(self, id: str) -> bool:
        """Check if an aggregate exists.

        Args:
            id: The aggregate identifier.

        Returns:
            True if the aggregate exists.
        """
        aggregate = await self._store.load(id, self._aggregate_class)
        return aggregate is not None

