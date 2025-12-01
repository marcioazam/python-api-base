"""Shared application infrastructure.

Provides common components for all bounded contexts:
- CQRS: Command/Query/Event buses and handlers
- Middleware: Transaction, validation, resilience, observability
- DTOs: Generic response types
- Exceptions: Application-level errors
- Mappers: Entity-DTO conversion

**Architecture: Vertical Slices - Shared Infrastructure**
"""

from .cqrs import (
    # Buses
    CommandBus,
    QueryBus,
    TypedEventBus,
    # Handlers
    CommandHandler,
    QueryHandler,
    EventHandler,
    # Types
    Command,
    Query,
    MiddlewareFunc,
    # Exceptions
    ApplicationError,
    ConflictError,
    ForbiddenError,
    HandlerNotFoundError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
    EventHandlerError,
)
from .middleware import (
    # Transaction
    Middleware,
    TransactionMiddleware,
    # Validation
    ValidationMiddleware,
    Validator,
    CompositeValidator,
    # Resilience
    RetryMiddleware,
    RetryConfig,
    CircuitBreakerMiddleware,
    CircuitBreakerConfig,
    ResilienceMiddleware,
    # Observability
    LoggingMiddleware,
    LoggingConfig,
    IdempotencyMiddleware,
    IdempotencyConfig,
)
from .dto import ApiResponse, PaginatedResponse, ProblemDetail
from .mapper import IMapper, Mapper

__all__ = [
    # CQRS
    "CommandBus",
    "QueryBus",
    "TypedEventBus",
    "CommandHandler",
    "QueryHandler",
    "EventHandler",
    "Command",
    "Query",
    "MiddlewareFunc",
    # Middleware
    "Middleware",
    "TransactionMiddleware",
    "ValidationMiddleware",
    "Validator",
    "CompositeValidator",
    "RetryMiddleware",
    "RetryConfig",
    "CircuitBreakerMiddleware",
    "CircuitBreakerConfig",
    "ResilienceMiddleware",
    "LoggingMiddleware",
    "LoggingConfig",
    "IdempotencyMiddleware",
    "IdempotencyConfig",
    # DTOs
    "ApiResponse",
    "PaginatedResponse",
    "ProblemDetail",
    # Exceptions
    "ApplicationError",
    "ValidationError",
    "NotFoundError",
    "ConflictError",
    "UnauthorizedError",
    "ForbiddenError",
    "HandlerNotFoundError",
    "EventHandlerError",
    # Mapper
    "IMapper",
    "Mapper",
]
