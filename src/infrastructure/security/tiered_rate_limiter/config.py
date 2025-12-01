"""Tiered rate limiter configuration.

**Feature: code-review-refactoring, Task 18.2: Refactor tiered_rate_limiter.py**
**Validates: Requirements 5.8**
"""

from dataclasses import dataclass

from pydantic import BaseModel

from .enums import UserTier


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
