"""Tiered rate limiter builder.

**Feature: code-review-refactoring, Task 18.2: Refactor tiered_rate_limiter.py**
**Validates: Requirements 5.8**
"""

from typing import Self

from .config import DEFAULT_TIER_LIMITS, RateLimitConfig
from .enums import UserTier
from .limiter import TieredRateLimiter
from .store import RateLimitStore


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

    def with_expensive_endpoints(
        self, endpoints: list[str], multiplier: float = 5.0
    ) -> Self:
        """Mark multiple endpoints as expensive."""
        for endpoint in endpoints:
            self._endpoint_multipliers[endpoint] = multiplier
        return self

    def build(self) -> TieredRateLimiter:
        """Build the configured TieredRateLimiter."""
        from .store import InMemoryRateLimitStore

        store = self._store or InMemoryRateLimitStore()
        return TieredRateLimiter(
            tier_limits=self._tier_limits,
            store=store,
            endpoint_multipliers=self._endpoint_multipliers,
        )


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
