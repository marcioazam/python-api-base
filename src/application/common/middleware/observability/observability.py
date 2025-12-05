"""Observability middleware for command bus.

Provides:
- LoggingMiddleware: Structured logging with correlation IDs
- IdempotencyMiddleware: Prevents duplicate command execution
- MetricsMiddleware: Command execution metrics and performance tracking

**Feature: enterprise-features-2025**
**Validates: Requirements 12.1, 12.2, 12.3, 12.4**
**Refactored: Split into logging_middleware.py, idempotency_middleware.py, metrics_middleware.py**
"""

# Re-export for backward compatibility
from application.common.middleware.observability.logging_middleware import (
    LoggingConfig,
    LoggingMiddleware,
    generate_request_id,
    get_request_id,
    request_id_var,
    set_request_id,
)
from application.common.middleware.observability.metrics_middleware import (
    InMemoryMetricsCollector,
    MetricsCollector,
    MetricsConfig,
    MetricsMiddleware,
)
from application.common.middleware.operations.idempotency_middleware import (
    IdempotencyCache,
    IdempotencyConfig,
    IdempotencyMiddleware,
    InMemoryIdempotencyCache,
)

__all__ = [
    # Idempotency
    "IdempotencyCache",
    "IdempotencyConfig",
    "IdempotencyMiddleware",
    "InMemoryIdempotencyCache",
    "InMemoryMetricsCollector",
    # Logging
    "LoggingConfig",
    "LoggingMiddleware",
    # Metrics
    "MetricsCollector",
    "MetricsConfig",
    "MetricsMiddleware",
    "generate_request_id",
    "get_request_id",
    "request_id_var",
    "set_request_id",
]
