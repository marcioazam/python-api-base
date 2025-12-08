"""Tests for event sourcing repository module.

Tests for EventSourcedRepository class.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from infrastructure.db.event_sourcing.aggregate import Aggregate
from infrastructure.db.event_sourcing.events import SourcedEvent
from infrastructure.db.event_sourcing.repository import EventSourcedRepository
from infrastructure.db.event_sourcing.store import EventStore


@dataclass(frozen=True)
class SampleEvent(SourcedEvent):
    """Sample event for testing."""

    data: str = ""


class SampleAggregate(Aggregate[str]):
    """Sample aggregate for testing."""

    def __init__(self, id: str = "") -> None:
        super().__init__(id)
        self._name = ""

    def apply_event(self, event: SourcedEvent) -> None:
        pass

    def to_snapshot_state(self) -> dict[str, Any]:
        return {"id": self._id, "name": self._name}


class TestEventSourcedRepository:
    """Tests for EventSourcedRepository class."""

    def test_init_stores_dependencies(self) -> None:
        """Repository should store event store and aggregate class."""
        store = MagicMock(spec=EventStore)
        repo = EventSourcedRepository(store, SampleAggregate)
        assert repo._store is store
        assert repo._aggregate_class is SampleAggregate

    def test_init_default_snapshot_frequency(self) -> None:
        """Repository should have default snapshot frequency of 100."""
        store = MagicMock(spec=EventStore)
        repo = EventSourcedRepository(store, SampleAggregate)
        assert repo._snapshot_frequency == 100

    def test_init_custom_snapshot_frequency(self) -> None:
        """Repository should accept custom snapshot frequency."""
        store = MagicMock(spec=EventStore)
        repo = EventSourcedRepository(store, SampleAggregate, snapshot_frequency=50)
        assert repo._snapshot_frequency == 50

    @pytest.mark.asyncio
    async def test_get_by_id_returns_aggregate(self) -> None:
        """get_by_id should return aggregate from store."""
        store = MagicMock(spec=EventStore)
        aggregate = SampleAggregate("agg-123")
        store.load = AsyncMock(return_value=aggregate)
        repo = EventSourcedRepository(store, SampleAggregate)

        result = await repo.get_by_id("agg-123")

        assert result is aggregate
        store.load.assert_called_once_with("agg-123", SampleAggregate)

    @pytest.mark.asyncio
    async def test_get_by_id_returns_none_when_not_found(self) -> None:
        """get_by_id should return None when aggregate not found."""
        store = MagicMock(spec=EventStore)
        store.load = AsyncMock(return_value=None)
        repo = EventSourcedRepository(store, SampleAggregate)

        result = await repo.get_by_id("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_save_calls_store_save(self) -> None:
        """save should call store.save with aggregate."""
        store = MagicMock(spec=EventStore)
        store.save = AsyncMock()
        repo = EventSourcedRepository(store, SampleAggregate, snapshot_frequency=0)
        aggregate = SampleAggregate("agg-123")

        await repo.save(aggregate)

        store.save.assert_called_once_with(aggregate, None)

    @pytest.mark.asyncio
    async def test_save_with_expected_version(self) -> None:
        """save should pass expected_version to store."""
        store = MagicMock(spec=EventStore)
        store.save = AsyncMock()
        repo = EventSourcedRepository(store, SampleAggregate, snapshot_frequency=0)
        aggregate = SampleAggregate("agg-123")

        await repo.save(aggregate, expected_version=5)

        store.save.assert_called_once_with(aggregate, 5)

    @pytest.mark.asyncio
    async def test_save_creates_snapshot_at_frequency(self) -> None:
        """save should create snapshot when version matches frequency."""
        store = MagicMock(spec=EventStore)
        store.save = AsyncMock()
        store.save_snapshot = AsyncMock()
        repo = EventSourcedRepository(store, SampleAggregate, snapshot_frequency=10)
        aggregate = SampleAggregate("agg-123")
        aggregate._version = 10  # Version matches frequency

        await repo.save(aggregate)

        store.save.assert_called_once()
        store.save_snapshot.assert_called_once_with(aggregate)

    @pytest.mark.asyncio
    async def test_save_no_snapshot_when_version_not_at_frequency(self) -> None:
        """save should not create snapshot when version doesn't match frequency."""
        store = MagicMock(spec=EventStore)
        store.save = AsyncMock()
        store.save_snapshot = AsyncMock()
        repo = EventSourcedRepository(store, SampleAggregate, snapshot_frequency=10)
        aggregate = SampleAggregate("agg-123")
        aggregate._version = 7  # Version doesn't match frequency

        await repo.save(aggregate)

        store.save.assert_called_once()
        store.save_snapshot.assert_not_called()

    @pytest.mark.asyncio
    async def test_save_no_snapshot_when_frequency_zero(self) -> None:
        """save should not create snapshot when frequency is 0."""
        store = MagicMock(spec=EventStore)
        store.save = AsyncMock()
        store.save_snapshot = AsyncMock()
        repo = EventSourcedRepository(store, SampleAggregate, snapshot_frequency=0)
        aggregate = SampleAggregate("agg-123")
        aggregate._version = 100

        await repo.save(aggregate)

        store.save.assert_called_once()
        store.save_snapshot.assert_not_called()

    @pytest.mark.asyncio
    async def test_exists_returns_true_when_found(self) -> None:
        """exists should return True when aggregate exists."""
        store = MagicMock(spec=EventStore)
        store.load = AsyncMock(return_value=SampleAggregate("agg-123"))
        repo = EventSourcedRepository(store, SampleAggregate)

        result = await repo.exists("agg-123")

        assert result is True

    @pytest.mark.asyncio
    async def test_exists_returns_false_when_not_found(self) -> None:
        """exists should return False when aggregate doesn't exist."""
        store = MagicMock(spec=EventStore)
        store.load = AsyncMock(return_value=None)
        repo = EventSourcedRepository(store, SampleAggregate)

        result = await repo.exists("nonexistent")

        assert result is False
