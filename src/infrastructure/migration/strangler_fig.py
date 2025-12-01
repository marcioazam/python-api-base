"""Strangler Fig Pattern implementation for gradual migration.

Provides routing for gradual migration from legacy to new systems.

**Feature: api-architecture-analysis, Property 12: Strangler fig pattern**
**Validates: Requirements 4.3**
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from collections.abc import Callable, Awaitable
import random
import re


class RoutingStrategy(str, Enum):
    """Strategy for routing requests."""

    LEGACY_ONLY = "legacy_only"
    NEW_ONLY = "new_only"
    PERCENTAGE = "percentage"
    HEADER_BASED = "header_based"
    USER_BASED = "user_based"
    FEATURE_FLAG = "feature_flag"


@dataclass(slots=True)
class RouteConfig:
    """Configuration for a route."""

    path_pattern: str
    strategy: RoutingStrategy
    new_percentage: float = 0.0
    header_name: str | None = None
    header_value: str | None = None
    allowed_users: set[str] = field(default_factory=set)
    feature_flag: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def matches_path(self, path: str) -> bool:
        """Check if path matches this route's pattern."""
        pattern = self.path_pattern.replace("*", ".*")
        return bool(re.match(f"^{pattern}$", path))


@dataclass(slots=True)
class RoutingDecision:
    """Result of a routing decision."""

    route_to_new: bool
    reason: str
    config: RouteConfig
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "route_to_new": self.route_to_new,
            "reason": self.reason,
            "path_pattern": self.config.path_pattern,
            "strategy": self.config.strategy.value,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass(slots=True)
class RoutingStats:
    """Statistics for routing decisions."""

    total_requests: int = 0
    legacy_requests: int = 0
    new_requests: int = 0
    errors: int = 0

    @property
    def new_percentage(self) -> float:
        """Get percentage routed to new system."""
        if self.total_requests == 0:
            return 0.0
        return self.new_requests / self.total_requests * 100

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_requests": self.total_requests,
            "legacy_requests": self.legacy_requests,
            "new_requests": self.new_requests,
            "errors": self.errors,
            "new_percentage": self.new_percentage,
        }


RequestContext = dict[str, Any]
Handler = Callable[[RequestContext], Awaitable[Any]]
FeatureFlagChecker = Callable[[str, RequestContext], Awaitable[bool]]


class StranglerRouter:
    """Router for strangler fig pattern."""

    def __init__(
        self,
        legacy_handler: Handler,
        new_handler: Handler,
        feature_flag_checker: FeatureFlagChecker | None = None,
    ):
        self._legacy_handler = legacy_handler
        self._new_handler = new_handler
        self._feature_flag_checker = feature_flag_checker
        self._routes: list[RouteConfig] = []
        self._stats: dict[str, RoutingStats] = {}
        self._default_strategy = RoutingStrategy.LEGACY_ONLY

    def add_route(self, config: RouteConfig) -> None:
        """Add a route configuration."""
        self._routes.append(config)
        self._stats[config.path_pattern] = RoutingStats()

    def remove_route(self, path_pattern: str) -> bool:
        """Remove a route configuration."""
        for i, route in enumerate(self._routes):
            if route.path_pattern == path_pattern:
                self._routes.pop(i)
                self._stats.pop(path_pattern, None)
                return True
        return False

    def get_route(self, path_pattern: str) -> RouteConfig | None:
        """Get a route configuration."""
        for route in self._routes:
            if route.path_pattern == path_pattern:
                return route
        return None

    def update_percentage(self, path_pattern: str, percentage: float) -> bool:
        """Update the new system percentage for a route."""
        route = self.get_route(path_pattern)
        if route:
            route.new_percentage = max(0.0, min(100.0, percentage))
            return True
        return False

    async def decide_route(
        self, path: str, context: RequestContext
    ) -> RoutingDecision:
        """Decide which system to route to."""
        for route in self._routes:
            if route.matches_path(path):
                return await self._apply_strategy(route, context)

        default_config = RouteConfig(
            path_pattern="*",
            strategy=self._default_strategy,
        )
        return RoutingDecision(
            route_to_new=False,
            reason="No matching route, using default",
            config=default_config,
        )

    async def _apply_strategy(
        self, config: RouteConfig, context: RequestContext
    ) -> RoutingDecision:
        """Apply routing strategy."""
        if config.strategy == RoutingStrategy.LEGACY_ONLY:
            return RoutingDecision(
                route_to_new=False,
                reason="Strategy: legacy only",
                config=config,
            )

        if config.strategy == RoutingStrategy.NEW_ONLY:
            return RoutingDecision(
                route_to_new=True,
                reason="Strategy: new only",
                config=config,
            )

        if config.strategy == RoutingStrategy.PERCENTAGE:
            roll = random.random() * 100
            route_to_new = roll < config.new_percentage
            return RoutingDecision(
                route_to_new=route_to_new,
                reason=f"Strategy: percentage ({config.new_percentage}%)",
                config=config,
            )

        if config.strategy == RoutingStrategy.HEADER_BASED:
            headers = context.get("headers", {})
            header_value = headers.get(config.header_name, "")
            route_to_new = header_value == config.header_value
            return RoutingDecision(
                route_to_new=route_to_new,
                reason=f"Strategy: header based ({config.header_name})",
                config=config,
            )

        if config.strategy == RoutingStrategy.USER_BASED:
            user_id = context.get("user_id", "")
            route_to_new = user_id in config.allowed_users
            return RoutingDecision(
                route_to_new=route_to_new,
                reason=f"Strategy: user based",
                config=config,
            )

        if config.strategy == RoutingStrategy.FEATURE_FLAG:
            if self._feature_flag_checker and config.feature_flag:
                route_to_new = await self._feature_flag_checker(
                    config.feature_flag, context
                )
            else:
                route_to_new = False
            return RoutingDecision(
                route_to_new=route_to_new,
                reason=f"Strategy: feature flag ({config.feature_flag})",
                config=config,
            )

        return RoutingDecision(
            route_to_new=False,
            reason="Unknown strategy, defaulting to legacy",
            config=config,
        )

    async def route(self, path: str, context: RequestContext) -> Any:
        """Route a request to the appropriate handler."""
        decision = await self.decide_route(path, context)
        stats = self._stats.get(decision.config.path_pattern)

        if stats:
            stats.total_requests += 1

        try:
            if decision.route_to_new:
                if stats:
                    stats.new_requests += 1
                return await self._new_handler(context)
            else:
                if stats:
                    stats.legacy_requests += 1
                return await self._legacy_handler(context)
        except Exception:
            if stats:
                stats.errors += 1
            raise

    def get_stats(self, path_pattern: str | None = None) -> dict[str, Any]:
        """Get routing statistics."""
        if path_pattern:
            stats = self._stats.get(path_pattern)
            return stats.to_dict() if stats else {}
        return {pattern: s.to_dict() for pattern, s in self._stats.items()}

    def list_routes(self) -> list[dict[str, Any]]:
        """List all route configurations."""
        return [
            {
                "path_pattern": r.path_pattern,
                "strategy": r.strategy.value,
                "new_percentage": r.new_percentage,
            }
            for r in self._routes
        ]


def create_migration_plan(
    routes: list[str],
    phases: int = 4,
) -> list[dict[str, Any]]:
    """Create a phased migration plan."""
    percentages = [25 * (i + 1) for i in range(phases)]
    plan: list[dict[str, Any]] = []

    for phase, percentage in enumerate(percentages, 1):
        plan.append({
            "phase": phase,
            "percentage": percentage,
            "routes": routes,
            "description": f"Route {percentage}% of traffic to new system",
        })

    return plan
