"""Event-driven cache invalidation strategy.

Provides automatic cache invalidation based on domain events to ensure
query cache consistency with domain state changes.

**Feature: application-layer-improvements-2025**
**Validates: Cache consistency requirements**

Example:
    >>> from application.common.middleware.cache_invalidation import (
    ...     CacheInvalidationStrategy,
    ... )
    >>> from application.common.cqrs.event_bus import EventBus
    >>>
    >>> # Setup
    >>> cache = InMemoryQueryCache()
    >>> invalidation = CacheInvalidationStrategy(cache)
    >>> event_bus = EventBus()
    >>>
    >>> # Register invalidation handlers
    >>> from domain.users.events import UserRegisteredEvent, UserEmailChangedEvent
    >>> event_bus.subscribe(UserRegisteredEvent, invalidation.on_user_registered)
    >>> event_bus.subscribe(UserEmailChangedEvent, invalidation.on_user_updated)
    >>>
    >>> # When events are published, cache is automatically invalidated
    >>> await event_bus.publish(UserEmailChangedEvent(user_id="123", ...))
    >>> # Cache entries matching "query_cache:*user:123*" are cleared
"""

import logging
from abc import ABC
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class QueryCache(Protocol):
    """Protocol for query cache (matches QueryCache from query_cache.py)."""

    async def clear_pattern(self, pattern: str) -> int:
        """Clear cached results matching pattern."""
        ...


# =============================================================================
# Cache Invalidation Strategy Base
# =============================================================================


@dataclass(frozen=True, slots=True)
class InvalidationRule:
    """Rule for cache invalidation.

    Defines which cache patterns to clear when a specific event occurs.

    Attributes:
        event_type: The domain event type that triggers invalidation.
        patterns: List of cache key patterns to clear (supports * wildcard).
        log_invalidation: Whether to log cache invalidation.
    """

    event_type: type
    patterns: list[str]
    log_invalidation: bool = True


class CacheInvalidationStrategy(ABC):
    """Base strategy for event-driven cache invalidation.

    Subclasses should define invalidation rules for domain events.

    Example:
        >>> class UserCacheInvalidation(CacheInvalidationStrategy):
        ...     def __init__(self, cache: QueryCache):
        ...         super().__init__(cache)
        ...         self.add_rule(
        ...             InvalidationRule(
        ...                 event_type=UserUpdatedEvent,
        ...                 patterns=[
        ...                     "query_cache:GetUserQuery:*",
        ...                     "query_cache:ListUsersQuery:*",
        ...                 ],
        ...             )
        ...         )
    """

    def __init__(self, cache: QueryCache) -> None:
        """Initialize cache invalidation strategy.

        Args:
            cache: Query cache to invalidate.
        """
        self._cache = cache
        self._rules: dict[type, InvalidationRule] = {}

    def add_rule(self, rule: InvalidationRule) -> None:
        """Add invalidation rule.

        Args:
            rule: The invalidation rule to add.
        """
        self._rules[rule.event_type] = rule

    async def invalidate(self, event: Any) -> None:
        """Invalidate cache based on event.

        Args:
            event: The domain event that triggered invalidation.
        """
        event_type = type(event)

        if event_type not in self._rules:
            # No invalidation rule for this event
            return

        rule = self._rules[event_type]

        total_cleared = 0
        for pattern in rule.patterns:
            cleared = await self._cache.clear_pattern(pattern)
            total_cleared += cleared

            if rule.log_invalidation and cleared > 0:
                logger.info(
                    "cache_invalidated",
                    extra={
                        "event_type": event_type.__name__,
                        "pattern": pattern,
                        "keys_cleared": cleared,
                        "operation": "CACHE_INVALIDATION",
                    },
                )

        if rule.log_invalidation and total_cleared > 0:
            logger.info(
                "cache_invalidation_completed",
                extra={
                    "event_type": event_type.__name__,
                    "total_keys_cleared": total_cleared,
                    "patterns_matched": len(rule.patterns),
                    "operation": "CACHE_INVALIDATION_COMPLETED",
                },
            )


# =============================================================================
# Domain-Specific Cache Invalidation Strategies
# =============================================================================


class UserCacheInvalidationStrategy(CacheInvalidationStrategy):
    """Cache invalidation strategy for User domain events.

    Automatically invalidates user-related query cache when:
    - User is created (invalidate user lists)
    - User is updated (invalidate specific user + lists)
    - User is deleted (invalidate specific user + lists)
    - User email is changed (invalidate specific user + email lookup)

    Example:
        >>> from domain.users.events import UserRegisteredEvent, UserEmailChangedEvent
        >>> from application.common.cqrs.event_bus import EventBus
        >>>
        >>> cache = InMemoryQueryCache()
        >>> strategy = UserCacheInvalidationStrategy(cache)
        >>> event_bus = EventBus()
        >>>
        >>> # Register handlers
        >>> event_bus.subscribe(UserRegisteredEvent, strategy.on_user_registered)
        >>> event_bus.subscribe(UserEmailChangedEvent, strategy.on_user_updated)
    """

    def __init__(self, cache: QueryCache) -> None:
        """Initialize user cache invalidation strategy.

        Args:
            cache: Query cache to invalidate.
        """
        super().__init__(cache)

        # Import domain events (lazy to avoid circular imports)
        try:
            from domain.users.events import (
                UserActivatedEvent,
                UserDeactivatedEvent,
                UserDeletedEvent,
                UserEmailChangedEvent,
                UserRegisteredEvent,
            )

            # User created - invalidate lists
            self.add_rule(
                InvalidationRule(
                    event_type=UserRegisteredEvent,
                    patterns=[
                        "query_cache:ListUsersQuery:*",
                        "query_cache:GetActiveUsersQuery:*",
                    ],
                )
            )

            # User updated - invalidate specific user + lists
            self.add_rule(
                InvalidationRule(
                    event_type=UserEmailChangedEvent,
                    patterns=[
                        "query_cache:GetUserQuery:*",
                        "query_cache:GetUserByEmailQuery:*",
                        "query_cache:ListUsersQuery:*",
                    ],
                )
            )

            # User activated/deactivated - invalidate specific user + active lists
            for event_type in [UserActivatedEvent, UserDeactivatedEvent]:
                self.add_rule(
                    InvalidationRule(
                        event_type=event_type,
                        patterns=[
                            "query_cache:GetUserQuery:*",
                            "query_cache:GetActiveUsersQuery:*",
                            "query_cache:ListUsersQuery:*",
                        ],
                    )
                )

            # User deleted - invalidate specific user + lists
            self.add_rule(
                InvalidationRule(
                    event_type=UserDeletedEvent,
                    patterns=[
                        "query_cache:GetUserQuery:*",
                        "query_cache:ListUsersQuery:*",
                    ],
                )
            )

        except ImportError:
            logger.warning(
                "Failed to import User domain events for cache invalidation. "
                "Cache invalidation will not work for User events."
            )

    async def on_user_registered(self, event: Any) -> None:
        """Handle user registered event.

        Args:
            event: UserRegisteredEvent.
        """
        await self.invalidate(event)

    async def on_user_updated(self, event: Any) -> None:
        """Handle user updated event.

        Args:
            event: Any user update event (EmailChanged, etc).
        """
        await self.invalidate(event)

    async def on_user_deleted(self, event: Any) -> None:
        """Handle user deleted event.

        Args:
            event: UserDeletedEvent.
        """
        await self.invalidate(event)


class ItemCacheInvalidationStrategy(CacheInvalidationStrategy):
    """Cache invalidation strategy for Item domain events.

    Example implementation for Item bounded context.
    """

    def __init__(self, cache: QueryCache) -> None:
        """Initialize item cache invalidation strategy.

        Args:
            cache: Query cache to invalidate.
        """
        super().__init__(cache)
        # Configure invalidation rules based on domain events as needed


# =============================================================================
# Helper Functions
# =============================================================================


def create_entity_specific_pattern(
    query_type: str, entity_id: str, prefix: str = "query_cache"
) -> str:
    """Create cache pattern for specific entity.

    Args:
        query_type: Query type name (e.g., "GetUserQuery").
        entity_id: Entity ID to match.
        prefix: Cache key prefix.

    Returns:
        Cache pattern with wildcard.

    Example:
        >>> pattern = create_entity_specific_pattern("GetUserQuery", "user-123")
        >>> # Returns: "query_cache:GetUserQuery:*user-123*"
    """
    return f"{prefix}:{query_type}:*{entity_id}*"


def create_query_type_pattern(query_type: str, prefix: str = "query_cache") -> str:
    """Create cache pattern for all queries of a type.

    Args:
        query_type: Query type name (e.g., "ListUsersQuery").
        prefix: Cache key prefix.

    Returns:
        Cache pattern with wildcard.

    Example:
        >>> pattern = create_query_type_pattern("ListUsersQuery")
        >>> # Returns: "query_cache:ListUsersQuery:*"
    """
    return f"{prefix}:{query_type}:*"


# =============================================================================
# Composite Cache Invalidation Strategy
# =============================================================================


class CompositeCacheInvalidationStrategy:
    """Combines multiple cache invalidation strategies.

    Useful when you have multiple bounded contexts and want to
    manage all cache invalidation in one place.

    Example:
        >>> cache = InMemoryQueryCache()
        >>> composite = CompositeCacheInvalidationStrategy(cache)
        >>>
        >>> # Add strategies for different domains
        >>> composite.add_strategy(UserCacheInvalidationStrategy(cache))
        >>> composite.add_strategy(ItemCacheInvalidationStrategy(cache))
        >>>
        >>> # Register with event bus
        >>> from domain.users.events import UserRegisteredEvent
        >>> event_bus.subscribe(UserRegisteredEvent, composite.on_event)
    """

    def __init__(self, cache: QueryCache) -> None:
        """Initialize composite strategy.

        Args:
            cache: Query cache to invalidate.
        """
        self._cache = cache
        self._strategies: list[CacheInvalidationStrategy] = []

    def add_strategy(self, strategy: CacheInvalidationStrategy) -> None:
        """Add a cache invalidation strategy.

        Args:
            strategy: The strategy to add.
        """
        self._strategies.append(strategy)

    async def on_event(self, event: Any) -> None:
        """Handle any domain event.

        Delegates to all registered strategies.

        Args:
            event: Domain event.
        """
        for strategy in self._strategies:
            await strategy.invalidate(event)


# =============================================================================
# Cache Invalidation Middleware (Optional Alternative)
# =============================================================================


class CacheInvalidationMiddleware:
    """Middleware that invalidates cache after command execution.

    Alternative to event-based invalidation - invalidates cache
    immediately after command completes successfully.

    Example:
        >>> from application.common.cqrs.command_bus import CommandBus
        >>>
        >>> cache = InMemoryQueryCache()
        >>> invalidation_mw = CacheInvalidationMiddleware(
        ...     cache,
        ...     invalidation_map={
        ...         CreateUserCommand: ["query_cache:ListUsersQuery:*"],
        ...         UpdateUserCommand: ["query_cache:GetUserQuery:*"],
        ...     },
        ... )
        >>> command_bus.add_middleware(invalidation_mw)
    """

    def __init__(
        self,
        cache: QueryCache,
        invalidation_map: dict[type, list[str]],
    ) -> None:
        """Initialize cache invalidation middleware.

        Args:
            cache: Query cache to invalidate.
            invalidation_map: Map of command type to cache patterns to clear.
        """
        self._cache = cache
        self._invalidation_map = invalidation_map

    async def __call__(
        self,
        command: Any,
        next_handler: Callable,
    ) -> Any:
        """Execute command and invalidate cache on success.

        Args:
            command: The command to execute.
            next_handler: The next handler in the chain.

        Returns:
            Result from handler.
        """
        # Execute command
        result = await next_handler(command)

        # Invalidate cache if command succeeded
        command_type = type(command)
        if command_type in self._invalidation_map:
            patterns = self._invalidation_map[command_type]

            for pattern in patterns:
                cleared = await self._cache.clear_pattern(pattern)

                if cleared > 0:
                    logger.debug(
                        "cache_invalidated_by_command",
                        extra={
                            "command_type": command_type.__name__,
                            "pattern": pattern,
                            "keys_cleared": cleared,
                            "operation": "COMMAND_CACHE_INVALIDATION",
                        },
                    )

        return result
