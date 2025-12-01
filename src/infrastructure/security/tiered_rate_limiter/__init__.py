"""Tiered Rate Limiting with user tier-based limits.

**Feature: code-review-refactoring, Task 18.2: Refactor tiered_rate_limiter.py**
**Validates: Requirements 5.8**
"""

from .builder import (
    TieredRateLimiterBuilder,
    configure_tiered_limiter,
    get_tiered_limiter,
)
from .config import DEFAULT_TIER_LIMITS, RateLimitConfig, RateLimitInfo
from .enums import UserTier
from .limiter import TieredRateLimiter
from .store import InMemoryRateLimitStore, RateLimitStore

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
