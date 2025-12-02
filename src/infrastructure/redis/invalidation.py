"""Cache invalidation strategies.

**Feature: enterprise-infrastructure-2025**
**Requirement: R2 - Cache Invalidation Strategies**
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING
from collections.abc import Callable, Coroutine

if TYPE_CHECKING:
    from infrastructure.redis.client import RedisClient

logger = logging.getLogger(__name__)


@dataclass
class InvalidationEvent:
    """Event that triggers cache invalidation.

    **Requirement: R2.4 - Log invalidation events with correlation ID**
    """

    entity_type: str
    entity_id: str | None = None
    action: str = "update"  # create, update, delete
    patterns: list[str] = field(default_factory=list)
    correlation_id: str | None = None


class InvalidationStrategy(ABC):
    """Base class for cache invalidation strategies.

    **Requirement: R2.3 - Support TTL-based, event-based, and manual strategies**
    """

    @abstractmethod
    async def invalidate(
        self,
        client: "RedisClient[Any]",
        event: InvalidationEvent,
    ) -> int:
        """Invalidate cache entries.

        Args:
            client: Redis client
            event: Invalidation event

        Returns:
            Number of entries invalidated
        """
        ...


class PatternInvalidation(InvalidationStrategy):
    """Pattern-based cache invalidation.

    **Requirement: R2.5 - Atomic batch invalidation**
    """

    def __init__(self, patterns: dict[str, list[str]] | None = None) -> None:
        """Initialize pattern invalidation.

        Args:
            patterns: Mapping of entity_type -> list of patterns
                     Patterns can use {entity_id} placeholder
        """
        self._patterns = patterns or {}

    def register_patterns(self, entity_type: str, patterns: list[str]) -> None:
        """Register patterns for an entity type.

        Args:
            entity_type: Entity type (e.g., "User", "Order")
            patterns: List of patterns (e.g., ["user:{entity_id}:*", "users:list"])
        """
        self._patterns[entity_type] = patterns

    async def invalidate(
        self,
        client: "RedisClient[Any]",
        event: InvalidationEvent,
    ) -> int:
        """Invalidate cache using patterns.

        Args:
            client: Redis client
            event: Invalidation event

        Returns:
            Number of entries invalidated
        """
        patterns = event.patterns or self._patterns.get(event.entity_type, [])
        total_deleted = 0

        for pattern in patterns:
            # Replace entity_id placeholder
            if event.entity_id and "{entity_id}" in pattern:
                pattern = pattern.replace("{entity_id}", event.entity_id)

            deleted = await client.delete_pattern(pattern)
            total_deleted += deleted

        logger.info(
            "Cache invalidated",
            extra={
                "entity_type": event.entity_type,
                "entity_id": event.entity_id,
                "action": event.action,
                "patterns": patterns,
                "deleted": total_deleted,
                "correlation_id": event.correlation_id,
            },
        )

        return total_deleted


class CacheInvalidator:
    """Central cache invalidation manager.

    **Requirement: R2.1 - Automatic invalidation on entity changes**
    **Requirement: R2.2 - Event-based invalidation**
    """

    def __init__(
        self,
        client: "RedisClient[Any]",
        strategy: InvalidationStrategy | None = None,
    ) -> None:
        """Initialize cache invalidator.

        Args:
            client: Redis client
            strategy: Invalidation strategy (default: PatternInvalidation)
        """
        self._client = client
        self._strategy = strategy or PatternInvalidation()
        self._listeners: list[Callable[[InvalidationEvent], Coroutine[Any, Any, None]]] = []

    def register_patterns(self, entity_type: str, patterns: list[str]) -> None:
        """Register cache patterns for an entity type.

        Args:
            entity_type: Entity type
            patterns: Cache key patterns
        """
        if isinstance(self._strategy, PatternInvalidation):
            self._strategy.register_patterns(entity_type, patterns)

    def add_listener(
        self,
        listener: Callable[[InvalidationEvent], Coroutine[Any, Any, None]],
    ) -> None:
        """Add invalidation event listener.

        Args:
            listener: Async callback for invalidation events
        """
        self._listeners.append(listener)

    async def on_create(
        self,
        entity_type: str,
        entity_id: str,
        patterns: list[str] | None = None,
        correlation_id: str | None = None,
    ) -> int:
        """Handle entity creation.

        **Requirement: R2.1 - Invalidate on create**

        Args:
            entity_type: Entity type
            entity_id: Entity ID
            patterns: Optional patterns override
            correlation_id: Request correlation ID

        Returns:
            Number of entries invalidated
        """
        event = InvalidationEvent(
            entity_type=entity_type,
            entity_id=entity_id,
            action="create",
            patterns=patterns or [],
            correlation_id=correlation_id,
        )
        return await self._invalidate(event)

    async def on_update(
        self,
        entity_type: str,
        entity_id: str,
        patterns: list[str] | None = None,
        correlation_id: str | None = None,
    ) -> int:
        """Handle entity update.

        **Requirement: R2.1 - Invalidate on update**

        Args:
            entity_type: Entity type
            entity_id: Entity ID
            patterns: Optional patterns override
            correlation_id: Request correlation ID

        Returns:
            Number of entries invalidated
        """
        event = InvalidationEvent(
            entity_type=entity_type,
            entity_id=entity_id,
            action="update",
            patterns=patterns or [],
            correlation_id=correlation_id,
        )
        return await self._invalidate(event)

    async def on_delete(
        self,
        entity_type: str,
        entity_id: str,
        patterns: list[str] | None = None,
        correlation_id: str | None = None,
    ) -> int:
        """Handle entity deletion.

        **Requirement: R2.1 - Invalidate on delete**

        Args:
            entity_type: Entity type
            entity_id: Entity ID
            patterns: Optional patterns override
            correlation_id: Request correlation ID

        Returns:
            Number of entries invalidated
        """
        event = InvalidationEvent(
            entity_type=entity_type,
            entity_id=entity_id,
            action="delete",
            patterns=patterns or [],
            correlation_id=correlation_id,
        )
        return await self._invalidate(event)

    async def invalidate_patterns(
        self,
        patterns: list[str],
        correlation_id: str | None = None,
    ) -> int:
        """Manually invalidate by patterns.

        Args:
            patterns: Patterns to invalidate
            correlation_id: Request correlation ID

        Returns:
            Number of entries invalidated
        """
        event = InvalidationEvent(
            entity_type="manual",
            patterns=patterns,
            correlation_id=correlation_id,
        )
        return await self._invalidate(event)

    async def _invalidate(self, event: InvalidationEvent) -> int:
        """Execute invalidation.

        Args:
            event: Invalidation event

        Returns:
            Number of entries invalidated
        """
        deleted = await self._strategy.invalidate(self._client, event)

        # Notify listeners
        for listener in self._listeners:
            try:
                await listener(event)
            except Exception as e:
                logger.warning(f"Invalidation listener failed: {e}")

        return deleted
