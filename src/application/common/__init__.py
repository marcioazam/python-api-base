"""Shared application infrastructure.

Provides common components for all bounded contexts:
- DTOs/Errors/Mappers/UseCases: Application base primitives
- CQRS: Command/Query/Event buses and handlers
- Middleware: Transaction, validation, resilience, observability
- Batch: Batch processing utilities
- Export: Data export/import services

**Architecture: Vertical Slices - Shared Infrastructure**
"""

# Base classes (directly from specialized subpackages)
from application.common.dto import ApiResponse, PaginatedResponse, ProblemDetail
from application.common.errors import (
    ApplicationError as BaseApplicationError,
    ConflictError as BaseConflictError,
    ForbiddenError as BaseForbiddenError,
    NotFoundError as BaseNotFoundError,
    UnauthorizedError as BaseUnauthorizedError,
    ValidationError as BaseValidationError,
)
from application.common.mappers import IMapper, Mapper
from application.common.use_cases import BaseUseCase

# CQRS
from application.common.cqrs import (
    # Exceptions
    ApplicationError,
    # Types
    Command,
    # Buses
    CommandBus,
    # Handlers
    CommandHandler,
    ConflictError,
    EventHandler,
    EventHandlerError,
    ForbiddenError,
    HandlerNotFoundError,
    MiddlewareFunc,
    NotFoundError,
    Query,
    QueryBus,
    QueryHandler,
    TypedEventBus,
    UnauthorizedError,
    ValidationError,
)

# Middleware
from application.common.middleware import (
    CircuitBreakerConfig,
    CircuitBreakerMiddleware,
    CompositeValidator,
    IdempotencyCache,
    IdempotencyMiddleware,
    LoggingMiddleware,
    # Observability
    MetricsMiddleware,
    # Transaction
    ResilienceMiddleware,
    RetryConfig,
    # Resilience
    RetryMiddleware,
    TransactionMiddleware,
    # Validation
    ValidationMiddleware,
    Validator,
)

__all__ = [
    # DTOs
    "ApiResponse",
    # Exceptions
    "ApplicationError",
    # Base Exceptions (re-exports)
    "BaseApplicationError",
    "BaseConflictError",
    "BaseForbiddenError",
    "BaseNotFoundError",
    "BaseUnauthorizedError",
    # UseCase
    "BaseUseCase",
    "BaseValidationError",
    "CircuitBreakerConfig",
    "CircuitBreakerMiddleware",
    "Command",
    # CQRS
    "CommandBus",
    "CommandHandler",
    "CompositeValidator",
    "ConflictError",
    "EventHandler",
    "EventHandlerError",
    "ForbiddenError",
    "HandlerNotFoundError",
    # Mapper
    "IMapper",
    "IdempotencyCache",
    "IdempotencyMiddleware",
    "LoggingMiddleware",
    "Mapper",
    "MetricsMiddleware",
    # Middleware
    "MiddlewareFunc",
    "NotFoundError",
    "PaginatedResponse",
    "ProblemDetail",
    "Query",
    "QueryBus",
    "QueryHandler",
    "ResilienceMiddleware",
    "RetryConfig",
    "RetryMiddleware",
    "TransactionMiddleware",
    "TypedEventBus",
    "UnauthorizedError",
    "ValidationError",
    "ValidationMiddleware",
    "Validator",
]
