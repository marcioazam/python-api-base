"""Middleware components for command/query pipelines.

Provides cross-cutting concerns:
- Transaction: Unit of work management
- Validation: Command validation
- Resilience: Retry, circuit breaker
- Observability: Logging, idempotency

**Architecture: Middleware Pattern**
"""

from .transaction import Middleware, TransactionMiddleware
from .validation import (
    ValidationMiddleware,
    Validator,
    CompositeValidator,
    RequiredFieldValidator,
    StringLengthValidator,
    RangeValidator,
)
from .resilience import (
    RetryMiddleware,
    RetryConfig,
    RetryExhaustedError,
    CircuitBreakerMiddleware,
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
    CircuitState,
    ResilienceMiddleware,
)
from .observability import (
    LoggingMiddleware,
    LoggingConfig,
    IdempotencyMiddleware,
    IdempotencyConfig,
    IdempotencyCache,
    InMemoryIdempotencyCache,
    get_request_id,
    set_request_id,
    generate_request_id,
)

__all__ = [
    # Transaction
    "Middleware",
    "TransactionMiddleware",
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
    "get_request_id",
    "set_request_id",
    "generate_request_id",
]
