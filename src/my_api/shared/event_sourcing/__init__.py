"""Event Sourcing pattern implementation.

Provides generic event store, aggregate base class, and event replay
capabilities for building event-sourced systems.

**Feature: code-review-refactoring, Task 1.9: Create __init__.py with re-exports**
**Validates: Requirements 1.2, 2.5**

This module has been refactored from a single file into a package.
All original exports are preserved for backward compatibility.

Original: event_sourcing.py (522 lines)
Refactored: event_sourcing/ package (8 files, ~60-130 lines each)

Usage:
    from my_api.shared.event_sourcing import (
        Aggregate,
        EventStore,
        InMemoryEventStore,
        SourcedEvent,
    )
"""

# Backward compatible re-exports
from .aggregate import Aggregate, AggregateId
from .events import EventStream, SourcedEvent
from .exceptions import ConcurrencyError
from .projections import InMemoryProjection, Projection
from .repository import EventSourcedRepository
from .snapshots import Snapshot
from .store import EventStore, InMemoryEventStore

__all__ = [
    # Events
    "SourcedEvent",
    "EventStream",
    # Snapshots
    "Snapshot",
    # Aggregate
    "Aggregate",
    "AggregateId",

    # Store
    "EventStore",
    "InMemoryEventStore",
    # Projections
    "Projection",
    "InMemoryProjection",
    # Repository
    "EventSourcedRepository",
    # Exceptions
    "ConcurrencyError",
]
