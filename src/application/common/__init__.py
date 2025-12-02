"""Shared application infrastructure.

Provides common components for all bounded contexts:
- Base: DTOs, Mappers, UseCases, Exceptions
- CQRS: Command/Query/Event buses and handlers
- Middleware: Transaction, validation, resilience, observability
- Batch: Batch processing utilities
- Export: Data export/import services

**Architecture: Vertical Slices - Shared Infrastructure**
"""

# Base classes
from application.common.base import (
    # DTOs
    ApiResponse,
    PaginatedResponse,
    ProblemDetail,
    # Mapper
    IMapper,
    Mapper,
    # UseCase
    BaseUseCase,
    # Exceptions (from base)
    ApplicationError as BaseApplicationError,
    ValidationError as BaseValidationError,
    NotFoundError as BaseNotFoundError,
    ConflictError as BaseConflictError,
    UnauthorizedError as BaseUnauthorizedError,
    ForbiddenError as BaseForbiddenError,
)

# CQRS
from application.common.cqrs import (
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

# Middleware
from application.common.middleware import (
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
    # UseCase
    "BaseUseCase",
]
