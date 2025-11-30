"""Event Sourced Repository adapter.

**Feature: code-review-refactoring, Task 1.8: Extract repository module**
**Validates: Requirements 2.1**
"""

from typing import Any

from .aggregate import Aggregate
from .events import SourcedEvent
from .store import EventStore


class EventSourcedRepository[AggregateT: Aggregate[Any], EventT: SourcedEvent]:
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
