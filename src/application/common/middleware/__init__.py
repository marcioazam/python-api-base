"""Middleware components for command/query pipelines.

Organized into subpackages by responsibility:
- cache/: Query caching and cache invalidation
- resilience/: Retry, circuit breaker, and resilience patterns
- observability/: Logging, metrics, and idempotency
- operations/: Transaction management
- validation/: Command validation

Provides cross-cutting concerns:
- Transaction: Unit of work management
- Validation: Command validation
- Resilience: Retry, circuit breaker
- Observability: Logging, idempotency, metrics
- Caching: Query result caching

**Architecture: Middleware Pattern**
**Feature: architecture-restructuring-2025**
"""

from application.common.middleware.cache import (
    CacheInvalidationStrategy,
    CompositeCacheInvalidationStrategy,
    InMemoryQueryCache,
    InvalidationRule,
    ItemCacheInvalidationStrategy,
    QueryCache,
    UserCacheInvalidationStrategy,
)
from application.common.middleware.observability import (
    InMemoryMetricsCollector,
    LoggingMiddleware,
    MetricsMiddleware,
)
from application.common.middleware.operations import (
    IdempotencyCache,
    IdempotencyMiddleware,
    InMemoryIdempotencyCache,
    TransactionMiddleware,
)
from application.common.middleware.resilience import (
    CircuitBreakerConfig,
    CircuitBreakerMiddleware,
    CircuitBreakerOpenError,
    CircuitState,
    ResilienceMiddleware,
    RetryConfig,
    RetryMiddleware,
)
from application.common.middleware.validation import (
    CompositeValidator,
    RangeValidator,
    RequiredFieldValidator,
    StringLengthValidator,
    ValidationMiddleware,
    Validator,
)

__all__ = [
    # Cache
    "CacheInvalidationStrategy",
    "CompositeCacheInvalidationStrategy",
    "InMemoryQueryCache",
    "InvalidationRule",
    "ItemCacheInvalidationStrategy",
    "QueryCache",
    "UserCacheInvalidationStrategy",
    # Resilience
    "CircuitBreakerConfig",
    "CircuitBreakerMiddleware",
    "CircuitBreakerOpenError",
    "CircuitState",
    "ResilienceMiddleware",
    "RetryConfig",
    "RetryMiddleware",
    # Observability
    "InMemoryMetricsCollector",
    "LoggingMiddleware",
    "MetricsMiddleware",
    # Operations
    "IdempotencyCache",
    "IdempotencyMiddleware",
    "InMemoryIdempotencyCache",
    "TransactionMiddleware",
    # Validation
    "CompositeValidator",
    "RangeValidator",
    "RequiredFieldValidator",
    "StringLengthValidator",
    "ValidationMiddleware",
    "Validator",
]
