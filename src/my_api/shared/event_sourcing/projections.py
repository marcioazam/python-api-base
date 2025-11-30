"""Event Sourcing projections for read models.

**Feature: code-review-refactoring, Task 1.7: Extract projections module**
**Validates: Requirements 2.3**
"""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any

from .events import SourcedEvent


class Projection[EventT: SourcedEvent](ABC):
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


class InMemoryProjection[EventT: SourcedEvent](Projection[EventT]):
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
