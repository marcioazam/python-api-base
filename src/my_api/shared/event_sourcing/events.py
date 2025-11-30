"""Event Sourcing events and event streams.

**Feature: code-review-refactoring, Task 1.3: Extract events module**
**Validates: Requirements 2.1**
"""

from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any
from uuid import uuid4


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
        default_factory=lambda: datetime.now(tz=UTC)
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
        default_factory=lambda: datetime.now(tz=UTC)
    )
    updated_at: datetime = field(
        default_factory=lambda: datetime.now(tz=UTC)
    )

    def append(self, event: SourcedEvent) -> None:
        """Append an event to the stream."""
        self.events.append(event)
        self.version = len(self.events)
        self.updated_at = datetime.now(tz=UTC)
