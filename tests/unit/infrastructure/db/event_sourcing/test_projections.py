"""Tests for event sourcing projections module.

Tests for Projection and InMemoryProjection classes.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest

from infrastructure.db.event_sourcing.events import SourcedEvent
from infrastructure.db.event_sourcing.projections import (
    InMemoryProjection,
    Projection,
)


@dataclass(frozen=True)
class UserCreatedEvent(SourcedEvent):
    """Sample event for testing."""

    user_id: str = ""
    username: str = ""
    email: str = ""


@dataclass(frozen=True)
class UserUpdatedEvent(SourcedEvent):
    """Sample update event for testing."""

    user_id: str = ""
    new_email: str = ""


class UserProjection(InMemoryProjection[SourcedEvent]):
    """Concrete projection for testing."""

    async def apply(self, event: SourcedEvent) -> None:
        """Apply event to projection."""
        if isinstance(event, UserCreatedEvent):
            self._state[event.user_id] = {
                "id": event.user_id,
                "username": event.username,
                "email": event.email,
            }
        elif isinstance(event, UserUpdatedEvent):
            if event.user_id in self._state:
                self._state[event.user_id]["email"] = event.new_email


class TestProjectionProtocol:
    """Tests for Projection abstract base class."""

    def test_is_abstract(self) -> None:
        """Projection should be abstract."""
        # Cannot instantiate directly
        with pytest.raises(TypeError):
            Projection()  # type: ignore

    def test_in_memory_projection_is_projection(self) -> None:
        """InMemoryProjection should be a Projection."""
        projection = UserProjection()
        assert isinstance(projection, Projection)


class TestInMemoryProjection:
    """Tests for InMemoryProjection class."""

    def test_init_empty_state(self) -> None:
        """Projection should start with empty state."""
        projection = UserProjection()
        assert projection.state == {}

    def test_init_zero_position(self) -> None:
        """Projection should start at position 0."""
        projection = UserProjection()
        assert projection.position == 0

    def test_state_returns_copy(self) -> None:
        """state property should return a copy."""
        projection = UserProjection()
        state1 = projection.state
        state1["test"] = "value"
        assert "test" not in projection.state

    @pytest.mark.asyncio
    async def test_apply_updates_state(self) -> None:
        """apply() should update projection state."""
        projection = UserProjection()
        event = UserCreatedEvent(
            user_id="user-1",
            username="john",
            email="john@example.com",
        )
        await projection.apply(event)
        assert "user-1" in projection._state
        assert projection._state["user-1"]["username"] == "john"

    @pytest.mark.asyncio
    async def test_apply_multiple_events(self) -> None:
        """apply() should handle multiple events."""
        projection = UserProjection()
        event1 = UserCreatedEvent(
            user_id="user-1",
            username="john",
            email="john@example.com",
        )
        event2 = UserCreatedEvent(
            user_id="user-2",
            username="jane",
            email="jane@example.com",
        )
        await projection.apply(event1)
        await projection.apply(event2)
        assert len(projection._state) == 2

    @pytest.mark.asyncio
    async def test_apply_update_event(self) -> None:
        """apply() should handle update events."""
        projection = UserProjection()
        create_event = UserCreatedEvent(
            user_id="user-1",
            username="john",
            email="john@example.com",
        )
        update_event = UserUpdatedEvent(
            user_id="user-1",
            new_email="john.new@example.com",
        )
        await projection.apply(create_event)
        await projection.apply(update_event)
        assert projection._state["user-1"]["email"] == "john.new@example.com"

    @pytest.mark.asyncio
    async def test_rebuild_clears_state(self) -> None:
        """rebuild() should clear existing state."""
        projection = UserProjection()
        projection._state["old"] = {"data": "value"}
        projection._position = 10
        events = [
            UserCreatedEvent(user_id="user-1", username="john", email="john@example.com")
        ]
        await projection.rebuild(events)
        assert "old" not in projection._state
        assert "user-1" in projection._state

    @pytest.mark.asyncio
    async def test_rebuild_resets_position(self) -> None:
        """rebuild() should reset position to 0 then increment."""
        projection = UserProjection()
        projection._position = 100
        events = [
            UserCreatedEvent(user_id="user-1", username="john", email="john@example.com"),
            UserCreatedEvent(user_id="user-2", username="jane", email="jane@example.com"),
        ]
        await projection.rebuild(events)
        assert projection.position == 2

    @pytest.mark.asyncio
    async def test_rebuild_empty_events(self) -> None:
        """rebuild() should handle empty event list."""
        projection = UserProjection()
        projection._state["old"] = {"data": "value"}
        await projection.rebuild([])
        assert projection.state == {}
        assert projection.position == 0

    @pytest.mark.asyncio
    async def test_rebuild_applies_all_events(self) -> None:
        """rebuild() should apply all events in order."""
        projection = UserProjection()
        events = [
            UserCreatedEvent(user_id="user-1", username="john", email="john@example.com"),
            UserUpdatedEvent(user_id="user-1", new_email="john.updated@example.com"),
            UserCreatedEvent(user_id="user-2", username="jane", email="jane@example.com"),
        ]
        await projection.rebuild(events)
        assert len(projection._state) == 2
        assert projection._state["user-1"]["email"] == "john.updated@example.com"
        assert projection.position == 3

    def test_position_property(self) -> None:
        """position property should return current position."""
        projection = UserProjection()
        projection._position = 42
        assert projection.position == 42
