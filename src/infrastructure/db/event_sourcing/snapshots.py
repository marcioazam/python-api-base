"""Event Sourcing snapshots for performance optimization.

**Feature: code-review-refactoring, Task 1.4: Extract snapshots module**
**Validates: Requirements 2.4**
"""

from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .aggregate import Aggregate


@dataclass
class Snapshot[AggregateT: "Aggregate[Any]"]:
    """Snapshot of aggregate state for performance optimization.

    Snapshots allow faster aggregate reconstruction by storing
    periodic state snapshots instead of replaying all events.

    **Feature: shared-modules-phase2, Property 10: Snapshot Hash Integrity**
    **Validates: Requirements 6.1**
    """

    aggregate_id: str
    aggregate_type: str
    version: int
    state: dict[str, Any]
    state_hash: str = ""  # SHA-256 hash of serialized state
    created_at: datetime = field(
        default_factory=lambda: datetime.now(tz=UTC)
    )

    @staticmethod
    def _compute_hash(state: dict[str, Any]) -> str:
        """Compute SHA-256 hash of state."""
        import hashlib
        import json

        serialized = json.dumps(state, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode()).hexdigest()

    def validate_hash(self) -> bool:
        """Validate that state_hash matches computed hash.

        **Feature: shared-modules-phase2, Property 11: Snapshot Validation Detection**
        **Validates: Requirements 6.2**

        Returns:
            True if hash is valid.
        """
        if not self.state_hash:
            return True  # No hash to validate
        return self._compute_hash(self.state) == self.state_hash

    @classmethod
    def from_aggregate(cls, aggregate: "Aggregate[Any]") -> "Snapshot[Any]":
        """Create a snapshot from an aggregate instance."""
        state = aggregate.to_snapshot_state()
        return cls(
            aggregate_id=str(aggregate.id),
            aggregate_type=aggregate.__class__.__name__,
            version=aggregate.version,
            state=state,
            state_hash=cls._compute_hash(state),
        )
