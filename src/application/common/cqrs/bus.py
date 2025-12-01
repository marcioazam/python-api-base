"""CQRS (Command Query Responsibility Segregation) infrastructure.

This module has been refactored into smaller, focused modules:
- exceptions.py: Shared exceptions
- event_bus.py: Event handling and TypedEventBus
- middleware.py: Middleware protocols and TransactionMiddleware
- command_bus.py: Command handling and CommandBus
- query_bus.py: Query handling and QueryBus

This file now serves as a compatibility layer, re-exporting all components.

**Feature: python-api-base-2025-state-of-art**
**Validates: Requirements 2.1, 2.2, 2.3, 2.4**
**Refactored: 2025 - Split 520 lines into 5 focused modules**
"""

# Re-export all components from refactored modules
from .exceptions import (
    ApplicationError,
    ConflictError,
    ForbiddenError,
    HandlerNotFoundError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)
from .event_bus import EventHandler, EventHandlerError, TypedEventBus
from .middleware import Middleware, TransactionMiddleware
from .validation_middleware import (
    ValidationMiddleware,
    Validator,
    CompositeValidator,
    RequiredFieldValidator,
    StringLengthValidator,
    RangeValidator,
)
from .resilience_middleware import (
    CircuitBreakerConfig,
    CircuitBreakerMiddleware,
    CircuitBreakerOpenError,
    CircuitState,
    ResilienceMiddleware,
    RetryConfig,
    RetryExhaustedError,
    RetryMiddleware,
)
from .observability_middleware import (
    IdempotencyCache,
    IdempotencyConfig,
    IdempotencyMiddleware,
    InMemoryIdempotencyCache,
    LoggingConfig,
    LoggingMiddleware,
    generate_request_id,
    get_request_id,
    set_request_id,
)
from .command_bus import (
    Command,
    CommandBus,
    CommandHandler,
    MiddlewareFunc,
)
from .query_bus import (
    Query,
    QueryBus,
    QueryHandler,
)

# Re-export all for public API
__all__ = [
    # Exceptions
    "ApplicationError",
    "ConflictError",
    "ForbiddenError",
    "HandlerNotFoundError",
    "NotFoundError",
    "UnauthorizedError",
    "ValidationError",
    # Event Bus
    "EventHandler",
    "EventHandlerError",
    "TypedEventBus",
    # Middleware
    "Middleware",
    "TransactionMiddleware",
    "MiddlewareFunc",
    # Validation Middleware
    "ValidationMiddleware",
    "Validator",
    "CompositeValidator",
    "RequiredFieldValidator",
    "StringLengthValidator",
    "RangeValidator",
    # Resilience Middleware
    "CircuitBreakerConfig",
    "CircuitBreakerMiddleware",
    "CircuitBreakerOpenError",
    "CircuitState",
    "ResilienceMiddleware",
    "RetryConfig",
    "RetryExhaustedError",
    "RetryMiddleware",
    # Observability Middleware
    "IdempotencyCache",
    "IdempotencyConfig",
    "IdempotencyMiddleware",
    "InMemoryIdempotencyCache",
    "LoggingConfig",
    "LoggingMiddleware",
    "generate_request_id",
    "get_request_id",
    "set_request_id",
    # Command Bus
    "Command",
    "CommandBus",
    "CommandHandler",
    # Query Bus
    "Query",
    "QueryBus",
    "QueryHandler",
]
