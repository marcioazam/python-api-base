"""Tiered Rate Limiting with user tier-based limits.

Provides rate limiting that varies based on user subscription tier,
supporting free, premium, and enterprise tiers with configurable limits.

**Feature: api-architecture-analysis, Task 6.1: Tiered Rate Limiting**
**Validates: Requirements 5.4**

Usage:
    from my_api.shared.tiered_rate_limiter import (
        TieredRateLimiter,
        UserTier,
        RateLimitConfig,
        get_tiered_limiter,
    )

    limiter = TieredRateLimiter()
    
    # Check rate limit
    allowed, info = await limiter.check_rate_limit(
        user_id="user-123",
        tier=UserTier.PREMIUM,
        endpoint="/api/items",
    )
"""

import asyncio
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol, Self

from pydantic import BaseModel


class UserTier(str, Enum):
    """User subscription tiers for rate limiting."""

    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"
    UNLIMITED = "unlimited"


@dataclass(frozen=True, slots=True)
class RateLimitConfig:
    """Configuration for a rate limit tier."""

    requests_per_minute: int
    requests_per_hour: int
    requests_per_day: int
    burst_limit: int = 10
    cost_multiplier: float = 1.0

    def scale(self, multiplier: float) -> "RateLimitConfig":
        """Create a scaled version of this config."""
        return RateLimitConfig(
            requests_per_minute=int(self.requests_per_minute * multiplier),
            requests_per_hour=int(self.requests_per_hour * multiplier),
            requests_per_day=int(self.requests_per_day * multiplier),
            burst_limit=int(self.burst_limit * multiplier),
            cost_multiplier=self.cost_multiplier,
        )


# Default tier configurations
DEFAULT_TIER_LIMITS: dict[UserTier, RateLimitConfig] = {
    UserTier.FREE: RateLimitConfig(
        requests_per_minute=10,
        requests_per_hour=100,
        requests_per_day=500,
        burst_limit=5,
    ),
    UserTier.BASIC: RateLimitConfig(
        requests_per_minute=30,
        requests_per_hour=500,
        requests_per_day=2000,
        burst_limit=10,
    ),
    UserTier.PREMIUM: RateLimitConfig(
        requests_per_minute=100,
        requests_per_hour=2000,
        requests_per_day=10000,
        burst_limit=20,
    ),
    UserTier.ENTERPRISE: RateLimitConfig(
        requests_per_minute=500,
        requests_per_hour=10000,
        requests_per_day=100000,
        burst_limit=50,
    ),
    UserTier.UNLIMITED: RateLimitConfig(
        requests_per_minute=999999,
        requests_per_hour=999999,
        requests_per_day=999999,
        burst_limit=999999,
    ),
}


class RateLimitInfo(BaseModel):
    """Information about current rate limit status."""

    tier: UserTier
    limit_minute: int
    limit_hour: int
    limit_day: int
    remaining_minute: int
    remaining_hour: int
    remaining_day: int
    reset_minute: int
    reset_hour: int
    reset_day: int
    retry_after: int | None = None

    @property
    def is_limited(self) -> bool:
        """Check if any limit is exceeded."""
        return (
            self.remaining_minute <= 0
            or self.remaining_hour <= 0
            or self.remaining_day <= 0
        )

    def to_headers(self) -> dict[str, str]:
        """Convert to HTTP headers."""
        headers = {
            "X-RateLimit-Tier": self.tier.value,
            "X-RateLimit-Limit-Minute": str(self.limit_minute),
            "X-RateLimit-Remaining-Minute": str(max(0, self.remaining_minute)),
            "X-RateLimit-Reset-Minute": str(self.reset_minute),
            "X-RateLimit-Limit-Hour": str(self.limit_hour),
            "X-RateLimit-Remaining-Hour": str(max(0, self.remaining_hour)),
            "X-RateLimit-Limit-Day": str(self.limit_day),
            "X-RateLimit-Remaining-Day": str(max(0, self.remaining_day)),
        }
        if self.retry_after is not None:
            headers["Retry-After"] = str(self.retry_after)
        return headers


class RateLimitStore(Protocol):
    """Protocol for rate limit storage backends."""

    async def get_count(self, key: str, window: int) -> int:
        """Get current count for a key within a time window."""
        ...

    async def increment(self, key: str, window: int, amount: int = 1) -> int:
        """Increment count for a key and return new value."""
        ...

    async def reset(self, key: str) -> None:
        """Reset count for a key."""
        ...

    async def get_ttl(self, key: str) -> int:
        """Get time-to-live for a key in seconds."""
        ...


@dataclass
class InMemoryRateLimitStore:
    """In-memory rate limit store for development/testing."""

    _counts: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    _timestamps: dict[str, float] = field(default_factory=dict)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def get_count(self, key: str, window: int) -> int:
        """Get current count for a key within a time window."""
        async with self._lock:
            now = time.time()
            timestamp = self._timestamps.get(key, now)
            
            if now - timestamp >= window:
                self._counts[key] = 0
                self._timestamps[key] = now
            
            return self._counts[key]

    async def increment(self, key: str, window: int, amount: int = 1) -> int:
        """Increment count for a key and return new value."""
        async with self._lock:
            now = time.time()
            timestamp = self._timestamps.get(key, now)
            
            if now - timestamp >= window:
                self._counts[key] = 0
                self._timestamps[key] = now
            
            self._counts[key] += amount
            return self._counts[key]

    async def reset(self, key: str) -> None:
        """Reset count for a key."""
        async with self._lock:
            self._counts[key] = 0
            self._timestamps.pop(key, None)

    async def get_ttl(self, key: str) -> int:
        """Get time-to-live for a key in seconds."""
        async with self._lock:
            timestamp = self._timestamps.get(key)
            if timestamp is None:
                return 0
            # Assume 60 second window for TTL calculation
            elapsed = time.time() - timestamp
            return max(0, int(60 - elapsed))


@dataclass
class TieredRateLimiter:
    """Rate limiter with tier-based limits.

    Supports multiple time windows (minute, hour, day) and
    configurable limits per user tier.
    """

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

    def _get_keys(self, user_id: str, endpoint: str | None = None) -> tuple[str, str, str]:
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
        """Check if a request is allowed under rate limits.

        Args:
            user_id: Unique identifier for the user.
            tier: User's subscription tier.
            endpoint: Optional endpoint for endpoint-specific limits.
            cost: Optional custom cost for this request.

        Returns:
            Tuple of (allowed, rate_limit_info).
        """
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
        """Record a request and return updated rate limit info.

        Args:
            user_id: Unique identifier for the user.
            tier: User's subscription tier.
            endpoint: Optional endpoint for endpoint-specific limits.
            cost: Optional custom cost for this request.

        Returns:
            Updated rate limit information.
        """
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


class TieredRateLimiterBuilder:
    """Fluent builder for TieredRateLimiter configuration."""

    def __init__(self) -> None:
        """Initialize builder with default configuration."""
        self._tier_limits = dict(DEFAULT_TIER_LIMITS)
        self._store: RateLimitStore | None = None
        self._endpoint_multipliers: dict[str, float] = {}

    def with_tier(self, tier: UserTier, config: RateLimitConfig) -> Self:
        """Configure a specific tier."""
        self._tier_limits[tier] = config
        return self

    def with_free_tier(
        self,
        requests_per_minute: int = 10,
        requests_per_hour: int = 100,
        requests_per_day: int = 500,
    ) -> Self:
        """Configure free tier limits."""
        self._tier_limits[UserTier.FREE] = RateLimitConfig(
            requests_per_minute=requests_per_minute,
            requests_per_hour=requests_per_hour,
            requests_per_day=requests_per_day,
        )
        return self

    def with_premium_tier(
        self,
        requests_per_minute: int = 100,
        requests_per_hour: int = 2000,
        requests_per_day: int = 10000,
    ) -> Self:
        """Configure premium tier limits."""
        self._tier_limits[UserTier.PREMIUM] = RateLimitConfig(
            requests_per_minute=requests_per_minute,
            requests_per_hour=requests_per_hour,
            requests_per_day=requests_per_day,
        )
        return self

    def with_enterprise_tier(
        self,
        requests_per_minute: int = 500,
        requests_per_hour: int = 10000,
        requests_per_day: int = 100000,
    ) -> Self:
        """Configure enterprise tier limits."""
        self._tier_limits[UserTier.ENTERPRISE] = RateLimitConfig(
            requests_per_minute=requests_per_minute,
            requests_per_hour=requests_per_hour,
            requests_per_day=requests_per_day,
        )
        return self

    def with_store(self, store: RateLimitStore) -> Self:
        """Set custom storage backend."""
        self._store = store
        return self

    def with_endpoint_cost(self, endpoint: str, multiplier: float) -> Self:
        """Set cost multiplier for an endpoint."""
        self._endpoint_multipliers[endpoint] = multiplier
        return self

    def with_expensive_endpoints(self, endpoints: list[str], multiplier: float = 5.0) -> Self:
        """Mark multiple endpoints as expensive."""
        for endpoint in endpoints:
            self._endpoint_multipliers[endpoint] = multiplier
        return self

    def build(self) -> TieredRateLimiter:
        """Build the configured TieredRateLimiter."""
        store = self._store or InMemoryRateLimitStore()
        return TieredRateLimiter(
            tier_limits=self._tier_limits,
            store=store,
            endpoint_multipliers=self._endpoint_multipliers,
        )


# Global instance for convenience
_default_limiter: TieredRateLimiter | None = None


def get_tiered_limiter() -> TieredRateLimiter:
    """Get the default tiered rate limiter instance."""
    global _default_limiter
    if _default_limiter is None:
        _default_limiter = TieredRateLimiter()
    return _default_limiter


def configure_tiered_limiter(limiter: TieredRateLimiter) -> None:
    """Set the default tiered rate limiter instance."""
    global _default_limiter
    _default_limiter = limiter


__all__ = [
    "DEFAULT_TIER_LIMITS",
    "InMemoryRateLimitStore",
    "RateLimitConfig",
    "RateLimitInfo",
    "RateLimitStore",
    "TieredRateLimiter",
    "TieredRateLimiterBuilder",
    "UserTier",
    "configure_tiered_limiter",
    "get_tiered_limiter",
]
