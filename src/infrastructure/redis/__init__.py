"""Redis infrastructure module.

Provides enterprise-grade Redis client with:
- Connection pooling
- Circuit breaker pattern
- Pydantic model serialization
- Automatic fallback to local cache

**Feature: enterprise-infrastructure-2025**
**Requirement: R1 - Redis Distributed Cache**
"""

from infrastructure.redis.client import RedisClient
from infrastructure.redis.config import RedisConfig
from infrastructure.redis.circuit_breaker import CircuitBreaker, CircuitState, CircuitOpenError
from infrastructure.redis.invalidation import (
    CacheInvalidator,
    InvalidationEvent,
    InvalidationStrategy,
    PatternInvalidation,
)

__all__ = [
    "RedisClient",
    "RedisConfig",
    "CircuitBreaker",
    "CircuitState",
    "CircuitOpenError",
    "CacheInvalidator",
    "InvalidationEvent",
    "InvalidationStrategy",
    "PatternInvalidation",
]
