"""Aggregate Root base class for DDD aggregates.

Extends BaseEntity with domain event collection capabilities.
Uses PEP 695 type parameter syntax (Python 3.12+).

**Feature: architecture-restructuring-2025**
**Validates: Requirements 1.3**
"""

from typing import Any

from pydantic import Field, PrivateAttr

from core.base.entity import BaseEntity
from core.base.domain_event import DomainEvent


class AggregateRoot[IdType: (str, int)](BaseEntity[IdType]):
    """Base class for aggregate roots in DDD.

    An aggregate root is the entry point to an aggregate - a cluster of
    domain objects that are treated as a single unit for data changes.

    Features:
    - Collects domain events that occurred during the aggregate's lifecycle
    - Provides methods to add, clear, and retrieve pending events
    - Tracks version for optimistic concurrency control

    Type Parameters:
        IdType: The type of the aggregate ID (str or int).
    """

    version: int = Field(
        default=1,
        description="Version number for optimistic concurrency control",
    )

    # Private attribute to store pending domain events
    _pending_events: list[DomainEvent] = PrivateAttr(default_factory=list)

    def add_event(self, event: DomainEvent) -> None:
        """Add a domain event to the pending events collection.

        Args:
            event: Domain event to add.
        """
        self._pending_events.append(event)

    def get_pending_events(self) -> list[DomainEvent]:
        """Get all pending domain events.

        Returns:
            List of pending domain events.
        """
        return list(self._pending_events)

    def clear_events(self) -> list[DomainEvent]:
        """Clear and return all pending domain events.

        This should be called after events have been dispatched.

        Returns:
            List of events that were cleared.
        """
        events = list(self._pending_events)
        self._pending_events.clear()
        return events

    def has_pending_events(self) -> bool:
        """Check if there are pending domain events.

        Returns:
            True if there are pending events, False otherwise.
        """
        return len(self._pending_events) > 0

    def increment_version(self) -> None:
        """Increment the version number for optimistic concurrency."""
        object.__setattr__(self, "version", self.version + 1)
        self.mark_updated()

    def apply_event(self, event: DomainEvent) -> None:
        """Apply a domain event to the aggregate.

        Override this method in subclasses to handle specific events.

        Args:
            event: Domain event to apply.
        """
        # Default implementation just adds the event
        self.add_event(event)

    def model_post_init(self, __context: Any) -> None:
        """Initialize private attributes after model creation."""
        super().model_post_init(__context)
        if not hasattr(self, "_pending_events"):
            object.__setattr__(self, "_pending_events", [])
