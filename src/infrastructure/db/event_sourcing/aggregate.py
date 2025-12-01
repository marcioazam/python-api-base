"""Event Sourcing aggregate base class.

Uses PEP 695 type parameter syntax (Python 3.12+) for cleaner generic definitions.

**Feature: code-review-refactoring, deep-code-quality-generics-review**
**Validates: Requirements 1.1, 2.1**
"""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any

from .events import SourcedEvent
from .snapshots import Snapshot


# Type alias for backward compatibility
type AggregateId = str | int


class Aggregate[AggregateIdT: (str, int)](ABC):
    """Base class for event-sourced aggregates.

    Aggregates are the consistency boundaries in event sourcing.
    They encapsulate state and behavior, and all state changes
    are recorded as events.

    Type Parameters:
        AggregateIdT: The type of the aggregate identifier.
    """

    def __init__(self, id: AggregateIdT) -> None:
        """Initialize aggregate.

        Args:
            id: Unique identifier for this aggregate.
        """
        self._id = id
        self._version = 0
        self._uncommitted_events: list[SourcedEvent] = []

    @property
    def id(self) -> AggregateIdT:
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
        versioned_event = self._create_versioned_event(event)
        self._apply_and_track(versioned_event)

    def _create_versioned_event(self, event: SourcedEvent) -> SourcedEvent:
        """Create a new event instance with the correct version."""
        from dataclasses import fields

        base_fields = {"event_id", "aggregate_id", "version", "timestamp", "metadata"}
        extra_kwargs = {}

        for f in fields(event):
            if f.name not in base_fields:
                extra_kwargs[f.name] = getattr(event, f.name)

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
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}

    def restore_from_snapshot_state(self, state: dict[str, Any]) -> None:
        """Restore aggregate state from a snapshot dictionary.

        Override this method to customize snapshot deserialization.

        Args:
            state: Dictionary representation of aggregate state.
        """
        for key, value in state.items():
            if hasattr(self, key):
                setattr(self, key, value)
