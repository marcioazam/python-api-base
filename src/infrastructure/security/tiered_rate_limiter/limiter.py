"""Tiered rate limiter implementation.

**Feature: code-review-refactoring, Task 18.2: Refactor tiered_rate_limiter.py**
**Validates: Requirements 5.8**
"""

import time
from dataclasses import dataclass, field
from typing import Self

from .config import DEFAULT_TIER_LIMITS, RateLimitConfig, RateLimitInfo
from .enums import UserTier
from .store import InMemoryRateLimitStore, RateLimitStore


@dataclass
class TieredRateLimiter:
    """Rate limiter with tier-based limits."""

    tier_limits: dict[UserTier, RateLimitConfig] = field(
        default_factory=lambda: dict(DEFAULT_TIER_LIMITS)
    )
    store: RateLimitStore = field(default_factory=InMemoryRateLimitStore)
    endpoint_multipliers: dict[str, float] = field(default_factory=dict)

    def configure_tier(self, tier: UserTier, config: RateLimitConfig) -> Self:
        """Configure limits for a specific tier."""
        self.tier_limits[tier] = config
        return self

    def configure_endpoint(self, endpoint: str, multiplier: float) -> Self:
        """Configure cost multiplier for an endpoint."""
        self.endpoint_multipliers[endpoint] = multiplier
        return self

    def get_config(self, tier: UserTier) -> RateLimitConfig:
        """Get configuration for a tier."""
        return self.tier_limits.get(tier, self.tier_limits[UserTier.FREE])

    def _get_keys(
        self, user_id: str, endpoint: str | None = None
    ) -> tuple[str, str, str]:
        """Generate storage keys for minute/hour/day windows."""
        base = f"ratelimit:{user_id}"
        if endpoint:
            base = f"{base}:{endpoint}"
        return (f"{base}:minute", f"{base}:hour", f"{base}:day")

    def _get_cost(self, endpoint: str | None, config: RateLimitConfig) -> int:
        """Calculate request cost based on endpoint multiplier."""
        if endpoint and endpoint in self.endpoint_multipliers:
            return int(self.endpoint_multipliers[endpoint] * config.cost_multiplier)
        return int(config.cost_multiplier)

    async def check_rate_limit(
        self,
        user_id: str,
        tier: UserTier,
        endpoint: str | None = None,
        cost: int | None = None,
    ) -> tuple[bool, RateLimitInfo]:
        """Check if a request is allowed under rate limits."""
        config = self.get_config(tier)
        request_cost = cost if cost is not None else self._get_cost(endpoint, config)

        key_minute, key_hour, key_day = self._get_keys(user_id, endpoint)

        count_minute = await self.store.get_count(key_minute, 60)
        count_hour = await self.store.get_count(key_hour, 3600)
        count_day = await self.store.get_count(key_day, 86400)

        remaining_minute = config.requests_per_minute - count_minute
        remaining_hour = config.requests_per_hour - count_hour
        remaining_day = config.requests_per_day - count_day

        ttl_minute = await self.store.get_ttl(key_minute)
        ttl_hour = await self.store.get_ttl(key_hour)
        ttl_day = await self.store.get_ttl(key_day)

        now = int(time.time())

        info = RateLimitInfo(
            tier=tier,
            limit_minute=config.requests_per_minute,
            limit_hour=config.requests_per_hour,
            limit_day=config.requests_per_day,
            remaining_minute=remaining_minute - request_cost,
            remaining_hour=remaining_hour - request_cost,
            remaining_day=remaining_day - request_cost,
            reset_minute=now + max(1, 60 - ttl_minute),
            reset_hour=now + max(1, 3600 - ttl_hour),
            reset_day=now + max(1, 86400 - ttl_day),
        )

        allowed = (
            remaining_minute >= request_cost
            and remaining_hour >= request_cost
            and remaining_day >= request_cost
        )

        if not allowed:
            if remaining_minute < request_cost:
                info.retry_after = max(1, 60 - ttl_minute)
            elif remaining_hour < request_cost:
                info.retry_after = max(1, 3600 - ttl_hour)
            else:
                info.retry_after = max(1, 86400 - ttl_day)

        return allowed, info

    async def record_request(
        self,
        user_id: str,
        tier: UserTier,
        endpoint: str | None = None,
        cost: int | None = None,
    ) -> RateLimitInfo:
        """Record a request and return updated rate limit info."""
        config = self.get_config(tier)
        request_cost = cost if cost is not None else self._get_cost(endpoint, config)

        key_minute, key_hour, key_day = self._get_keys(user_id, endpoint)

        count_minute = await self.store.increment(key_minute, 60, request_cost)
        count_hour = await self.store.increment(key_hour, 3600, request_cost)
        count_day = await self.store.increment(key_day, 86400, request_cost)

        now = int(time.time())

        return RateLimitInfo(
            tier=tier,
            limit_minute=config.requests_per_minute,
            limit_hour=config.requests_per_hour,
            limit_day=config.requests_per_day,
            remaining_minute=config.requests_per_minute - count_minute,
            remaining_hour=config.requests_per_hour - count_hour,
            remaining_day=config.requests_per_day - count_day,
            reset_minute=now + 60,
            reset_hour=now + 3600,
            reset_day=now + 86400,
        )

    async def reset_limits(self, user_id: str, endpoint: str | None = None) -> None:
        """Reset all rate limits for a user."""
        key_minute, key_hour, key_day = self._get_keys(user_id, endpoint)
        await self.store.reset(key_minute)
        await self.store.reset(key_hour)
        await self.store.reset(key_day)
