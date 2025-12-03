"""Middleware components for command/query pipelines.

Provides cross-cutting concerns:
- Transaction: Unit of work management
- Validation: Command validation
- Resilience: Retry, circuit breaker
- Observability: Logging, idempotency, metrics
- Caching: Query result caching

**Architecture: Middleware Pattern**
"""

from application.common.middleware.transaction import (
    Middleware,
    TransactionMiddleware,
    TransactionConfig,
    DEFAULT_TRANSACTION_CONFIG,
)
from application.common.middleware.validation import (
    ValidationMiddleware,
    Validator,
    CompositeValidator,
    RequiredFieldValidator,
    StringLengthValidator,
    RangeValidator,
)
from application.common.middleware.retry import (
    RetryMiddleware,
    RetryConfig,
    RetryExhaustedError,
)
from application.common.middleware.circuit_breaker import (
    CircuitBreakerMiddleware,
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
    CircuitState,
)
from application.common.middleware.resilience import ResilienceMiddleware
from application.common.middleware.observability import (
    LoggingMiddleware,
    LoggingConfig,
    IdempotencyMiddleware,
    IdempotencyConfig,
    IdempotencyCache,
    InMemoryIdempotencyCache,
    MetricsMiddleware,
    MetricsConfig,
    MetricsCollector,
    InMemoryMetricsCollector,
    get_request_id,
    set_request_id,
    generate_request_id,
)
from application.common.middleware.query_cache import (
    QueryCacheMiddleware,
    QueryCacheConfig,
    QueryCache,
    InMemoryQueryCache,
)
from application.common.middleware.cache_invalidation import (
    CacheInvalidationStrategy,
    UserCacheInvalidationStrategy,
    ItemCacheInvalidationStrategy,
    CompositeCacheInvalidationStrategy,
    CacheInvalidationMiddleware,
    InvalidationRule,
    create_entity_specific_pattern,
    create_query_type_pattern,
)

__all__ = [
    # Transaction
    "Middleware",
    "TransactionMiddleware",
    "TransactionConfig",
    "DEFAULT_TRANSACTION_CONFIG",
    # Validation
    "ValidationMiddleware",
    "Validator",
    "CompositeValidator",
    "RequiredFieldValidator",
    "StringLengthValidator",
    "RangeValidator",
    # Resilience
    "RetryMiddleware",
    "RetryConfig",
    "RetryExhaustedError",
    "CircuitBreakerMiddleware",
    "CircuitBreakerConfig",
    "CircuitBreakerOpenError",
    "CircuitState",
    "ResilienceMiddleware",
    # Observability
    "LoggingMiddleware",
    "LoggingConfig",
    "IdempotencyMiddleware",
    "IdempotencyConfig",
    "IdempotencyCache",
    "InMemoryIdempotencyCache",
    "MetricsMiddleware",
    "MetricsConfig",
    "MetricsCollector",
    "InMemoryMetricsCollector",
    "get_request_id",
    "set_request_id",
    "generate_request_id",
    # Query Caching
    "QueryCacheMiddleware",
    "QueryCacheConfig",
    "QueryCache",
    "InMemoryQueryCache",
    # Cache Invalidation
    "CacheInvalidationStrategy",
    "UserCacheInvalidationStrategy",
    "ItemCacheInvalidationStrategy",
    "CompositeCacheInvalidationStrategy",
    "CacheInvalidationMiddleware",
    "InvalidationRule",
    "create_entity_specific_pattern",
    "create_query_type_pattern",
]
