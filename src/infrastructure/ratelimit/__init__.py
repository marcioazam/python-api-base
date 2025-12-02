"""Generic rate limiting infrastructure with PEP 695 type parameters.

**Feature: enterprise-generics-2025**
**Requirement: R5 - Generic Rate Limiter**

Exports:
    - RateLimiter[TClient]: Generic rate limiter
    - RateLimitResult[TClient]: Typed result
    - RateLimitConfig: Configuration
    - SlidingWindowLimiter: Redis-backed implementation
    - RateLimitMiddleware: FastAPI middleware
"""

from infrastructure.ratelimit.config import RateLimitConfig, RateLimit
from infrastructure.ratelimit.limiter import (
    RateLimiter,
    RateLimitResult,
    SlidingWindowLimiter,
    InMemoryRateLimiter,
)
from infrastructure.ratelimit.middleware import (
    RateLimitMiddleware,
    IPClientExtractor,
    UserIdExtractor,
    APIKeyExtractor,
    rate_limit,
)

__all__ = [
    # Config
    "RateLimitConfig",
    "RateLimit",
    # Core
    "RateLimiter",
    "RateLimitResult",
    "SlidingWindowLimiter",
    "InMemoryRateLimiter",
    # Middleware
    "RateLimitMiddleware",
    "IPClientExtractor",
    "UserIdExtractor",
    "APIKeyExtractor",
    "rate_limit",
]
