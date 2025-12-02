"""User event projections for updating read models.

Projections listen to domain events and update read models
to maintain eventually consistent query-optimized views.

**Feature: architecture-restructuring-2025**
**Validates: Requirements 4.2, 4.4**
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Protocol

from core.base.domain_event import DomainEvent
from domain.users.events import (
    UserRegisteredEvent,
    UserDeactivatedEvent,
    UserEmailChangedEvent,
    UserEmailVerifiedEvent,
    UserLoggedInEvent,
    UserProfileUpdatedEvent,
    UserReactivatedEvent,
)

logger = logging.getLogger(__name__)


class IUserReadModelRepository(Protocol):
    """Interface for user read model persistence."""

    async def create(self, user_data: dict[str, Any]) -> None:
        """Create a new user read model entry."""
        ...

    async def update(self, user_id: str, updates: dict[str, Any]) -> None:
        """Update an existing user read model entry."""
        ...

    async def delete(self, user_id: str) -> None:
        """Delete a user read model entry."""
        ...

    async def get_by_id(self, user_id: str) -> dict[str, Any] | None:
        """Get user read model by ID."""
        ...


class ProjectionHandler(ABC):
    """Base class for projection handlers."""

    @abstractmethod
    async def handle(self, event: DomainEvent) -> None:
        """Handle a domain event and update read models."""
        ...

    @property
    @abstractmethod
    def handled_events(self) -> tuple[type[DomainEvent], ...]:
        """Return tuple of event types this handler processes."""
        ...


@dataclass
class UserProjectionHandler(ProjectionHandler):
    """Handles user domain events and updates read models.

    This projection handler listens to user-related domain events
    and maintains the user read model for efficient queries.
    """

    repository: IUserReadModelRepository

    @property
    def handled_events(self) -> tuple[type[DomainEvent], ...]:
        """Return tuple of event types this handler processes."""
        return (
            UserRegisteredEvent,
            UserDeactivatedEvent,
            UserEmailChangedEvent,
            UserEmailVerifiedEvent,
            UserLoggedInEvent,
            UserProfileUpdatedEvent,
            UserReactivatedEvent,
        )

    async def handle(self, event: DomainEvent) -> None:
        """Handle a domain event and update read models."""
        handler_map = {
            UserRegisteredEvent: self._handle_user_registered,
            UserDeactivatedEvent: self._handle_user_deactivated,
            UserEmailChangedEvent: self._handle_email_changed,
            UserEmailVerifiedEvent: self._handle_email_verified,
            UserLoggedInEvent: self._handle_user_logged_in,
            UserProfileUpdatedEvent: self._handle_profile_updated,
            UserReactivatedEvent: self._handle_user_reactivated,
        }

        handler = handler_map.get(type(event))
        if handler:
            await handler(event)
            logger.debug(
                f"Processed {type(event).__name__} for projection",
                extra={"event_id": str(event.event_id)},
            )
        else:
            logger.warning(f"No handler for event type: {type(event).__name__}")

    async def _handle_user_registered(self, event: UserRegisteredEvent) -> None:
        """Handle UserRegisteredEvent - create new read model entry."""
        await self.repository.create({
            "id": event.user_id,
            "email": event.email,
            "is_active": True,
            "is_verified": False,
            "created_at": event.occurred_at,
            "updated_at": event.occurred_at,
        })

    async def _handle_user_deactivated(self, event: UserDeactivatedEvent) -> None:
        """Handle UserDeactivatedEvent - mark user as inactive."""
        await self.repository.update(
            event.user_id,
            {
                "is_active": False,
                "deactivation_reason": event.reason,
                "updated_at": event.occurred_at,
            },
        )

    async def _handle_email_changed(self, event: UserEmailChangedEvent) -> None:
        """Handle UserEmailChangedEvent - update email."""
        await self.repository.update(
            event.user_id,
            {
                "email": event.new_email,
                "is_verified": False,  # Reset verification on email change
                "updated_at": event.occurred_at,
            },
        )

    async def _handle_email_verified(self, event: UserEmailVerifiedEvent) -> None:
        """Handle UserEmailVerifiedEvent - mark email as verified."""
        await self.repository.update(
            event.user_id,
            {
                "is_verified": True,
                "updated_at": event.occurred_at,
            },
        )

    async def _handle_user_logged_in(self, event: UserLoggedInEvent) -> None:
        """Handle UserLoggedInEvent - update last login timestamp."""
        await self.repository.update(
            event.user_id,
            {
                "last_login_at": event.occurred_at,
            },
        )

    async def _handle_profile_updated(self, event: UserProfileUpdatedEvent) -> None:
        """Handle UserProfileUpdatedEvent - update profile fields."""
        await self.repository.update(
            event.user_id,
            {
                "updated_at": event.occurred_at,
            },
        )

    async def _handle_user_reactivated(self, event: UserReactivatedEvent) -> None:
        """Handle UserReactivatedEvent - mark user as active."""
        await self.repository.update(
            event.user_id,
            {
                "is_active": True,
                "deactivation_reason": None,
                "updated_at": event.occurred_at,
            },
        )


class UserReadModelProjector:
    """Orchestrates user read model projections.

    Manages multiple projection handlers and routes events
    to appropriate handlers.
    """

    def __init__(self, handlers: list[ProjectionHandler] | None = None) -> None:
        self._handlers: list[ProjectionHandler] = handlers or []
        self._event_handler_map: dict[type[DomainEvent], list[ProjectionHandler]] = {}
        self._build_handler_map()

    def _build_handler_map(self) -> None:
        """Build mapping from event types to handlers."""
        for handler in self._handlers:
            for event_type in handler.handled_events:
                if event_type not in self._event_handler_map:
                    self._event_handler_map[event_type] = []
                self._event_handler_map[event_type].append(handler)

    def register_handler(self, handler: ProjectionHandler) -> None:
        """Register a new projection handler."""
        self._handlers.append(handler)
        for event_type in handler.handled_events:
            if event_type not in self._event_handler_map:
                self._event_handler_map[event_type] = []
            self._event_handler_map[event_type].append(handler)

    async def project(self, event: DomainEvent) -> None:
        """Project an event to all registered handlers."""
        handlers = self._event_handler_map.get(type(event), [])

        for handler in handlers:
            try:
                await handler.handle(event)
            except Exception as e:
                logger.error(
                    f"Projection handler failed: {e}",
                    extra={
                        "event_type": type(event).__name__,
                        "event_id": str(event.event_id),
                        "handler": type(handler).__name__,
                    },
                    exc_info=True,
                )
                # Continue with other handlers even if one fails

    async def rebuild_from_events(self, events: list[DomainEvent]) -> int:
        """Rebuild read models from a list of events.

        Args:
            events: List of domain events in chronological order.

        Returns:
            Number of events processed.
        """
        processed = 0
        for event in events:
            await self.project(event)
            processed += 1

        logger.info(f"Rebuilt read models from {processed} events")
        return processed
