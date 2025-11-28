"""Event Sourcing snapshots for performance optimization.

**Feature: code-review-refactoring, Task 1.4: Extract snapshots module**
**Validates: Requirements 2.4**
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Generic, TypeVar

if TYPE_CHECKING:
    from .aggregate import Aggregate

AggregateT = TypeVar("AggregateT", bound="Aggregate[Any]")


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
