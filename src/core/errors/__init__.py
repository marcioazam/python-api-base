"""Core error hierarchy.

**Feature: architecture-restructuring-2025**
"""

from my_app.core.errors.domain_errors import (
    AppException,
    AuthenticationError,
    AuthorizationError,
    BusinessRuleViolationError,
    ConflictError,
    EntityNotFoundError,
    ErrorContext,
    RateLimitExceededError,
    ValidationError,
)
from my_app.core.errors.application_errors import (
    ApplicationError,
    CommandHandlerError,
    ConcurrencyError,
    HandlerNotFoundError,
    InvalidCommandError,
    InvalidQueryError,
    QueryHandlerError,
    TransactionError,
    UseCaseError,
)
from my_app.core.errors.infrastructure_errors import (
    InfrastructureError,
    DatabaseError,
    ExternalServiceError,
)

__all__ = [
    "AppException",
    "ApplicationError",
    "AuthenticationError",
    "AuthorizationError",
    "BusinessRuleViolationError",
    "CommandHandlerError",
    "ConcurrencyError",
    "ConflictError",
    "DatabaseError",
    "EntityNotFoundError",
    "ErrorContext",
    "ExternalServiceError",
    "HandlerNotFoundError",
    "InfrastructureError",
    "InvalidCommandError",
    "InvalidQueryError",
    "QueryHandlerError",
    "RateLimitExceededError",
    "TransactionError",
    "UseCaseError",
    "ValidationError",
]
