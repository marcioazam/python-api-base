"""Rate limiter configuration with PEP 695 generics.

**Feature: enterprise-generics-2025**
**Requirement: R5.1, R5.4, R5.6**
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from enum import Enum


class RateLimitAlgorithm(Enum):
    """Rate limiting algorithm types."""

    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"
    TOKEN_BUCKET = "token_bucket"
    LEAKY_BUCKET = "leaky_bucket"


@dataclass(frozen=True, slots=True)
class RateLimit:
    """Rate limit configuration.

    **Requirement: R5.6 - Per-endpoint limits**

    Attributes:
        requests: Maximum number of requests allowed.
        window: Time window for the limit.
        burst: Optional burst allowance above limit.
    """

    requests: int
    window: timedelta
    burst: int = 0

    @property
    def window_seconds(self) -> float:
        """Get window duration in seconds."""
        return self.window.total_seconds()

    def __post_init__(self) -> None:
        """Validate configuration."""
        if self.requests <= 0:
            raise ValueError("requests must be positive")
        if self.window.total_seconds() <= 0:
            raise ValueError("window must be positive")
        if self.burst < 0:
            raise ValueError("burst cannot be negative")


@dataclass(frozen=True, slots=True)
class RateLimitConfig:
    """Global rate limiter configuration.

    **Requirement: R5.4 - Sliding window algorithm**

    Attributes:
        algorithm: Rate limiting algorithm to use.
        redis_url: Redis connection URL for distributed limiting.
        key_prefix: Prefix for Redis keys.
        default_limit: Default rate limit if none specified.
        enabled: Whether rate limiting is enabled.
    """

    algorithm: RateLimitAlgorithm = RateLimitAlgorithm.SLIDING_WINDOW
    redis_url: str = "redis://localhost:6379/0"
    key_prefix: str = "ratelimit:"
    default_limit: RateLimit = field(
        default_factory=lambda: RateLimit(requests=100, window=timedelta(minutes=1))
    )
    enabled: bool = True

    def get_redis_key(self, client_id: str, endpoint: str = "default") -> str:
        """Generate Redis key for rate limit tracking.

        Args:
            client_id: Client identifier.
            endpoint: Endpoint identifier.

        Returns:
            Redis key string.
        """
        return f"{self.key_prefix}{endpoint}:{client_id}"


# =============================================================================
# Preset Configurations
# =============================================================================


# Standard API limits
API_RATE_LIMITS: dict[str, RateLimit] = {
    "default": RateLimit(requests=100, window=timedelta(minutes=1)),
    "auth": RateLimit(requests=10, window=timedelta(minutes=1)),
    "search": RateLimit(requests=30, window=timedelta(minutes=1)),
    "upload": RateLimit(requests=5, window=timedelta(minutes=1)),
    "webhook": RateLimit(requests=1000, window=timedelta(minutes=1)),
}


def get_rate_limit(endpoint: str) -> RateLimit:
    """Get rate limit for endpoint.

    Args:
        endpoint: Endpoint name or pattern.

    Returns:
        RateLimit configuration.
    """
    return API_RATE_LIMITS.get(endpoint, API_RATE_LIMITS["default"])
