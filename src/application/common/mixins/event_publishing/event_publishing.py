"""Event publishing mixin for use cases.

Provides reusable event publishing functionality for use cases.

**Feature: application-layer-code-review-2025**
**Extracted from: examples/item/use_case.py**
"""

import logging
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class HasEvents(Protocol):
    """Protocol for entities with domain events."""

    @property
    def events(self) -> list[Any]: ...
    def clear_events(self) -> None: ...


class EventBusProtocol(Protocol):
    """Protocol for event bus."""

    async def publish(self, event: Any, **kwargs: Any) -> None: ...


class EventPublishingMixin:
    """Mixin for publishing domain events from entities.

    Provides reusable event publishing functionality that can be
    mixed into use cases.

    Example:
        >>> class MyUseCase(EventPublishingMixin):
        ...     def __init__(self, event_bus: EventBusProtocol | None = None):
        ...         self._event_bus = event_bus
        ...
        ...     async def do_something(self, entity: HasEvents) -> None:
        ...         # ... business logic ...
        ...         await self._publish_entity_events(entity)
    """

    _event_bus: EventBusProtocol | None

    async def _publish_entity_events(
        self,
        entity: HasEvents,
        *,
        raise_on_error: bool = False,
    ) -> None:
        """Publish all domain events from an entity.

        Args:
            entity: Entity with domain events.
            raise_on_error: If True, raises on first handler failure.
        """
        if not self._event_bus:
            return

        for event in entity.events:
            try:
                await self._event_bus.publish(event, raise_on_error=raise_on_error)
            except Exception as e:
                logger.error(
                    f"Failed to publish event {type(event).__name__}: {e}",
                    extra={"event_type": type(event).__name__, "error": str(e)},
                )
                if raise_on_error:
                    raise

        entity.clear_events()

    async def _publish_events(self, entity: HasEvents) -> None:
        """Shortcut for publishing events without raising on error.

        Args:
            entity: Entity with domain events.
        """
        await self._publish_entity_events(entity, raise_on_error=False)
