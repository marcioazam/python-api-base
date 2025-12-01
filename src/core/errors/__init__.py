"""Core error hierarchy.

**Feature: architecture-restructuring-2025**
**Feature: interface-layer-generics-review**
"""

from core.errors.domain_errors import (
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
from core.errors.application_errors import (
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
from core.errors.infrastructure_errors import (
    InfrastructureError,
    DatabaseError,
    ExternalServiceError,
)
from core.errors.constants import (
    HttpStatus,
    ErrorCode,
    ErrorCodes,
    ErrorMessages,
)
from core.errors.status import (
    OperationStatus,
    ValidationStatus,
    EntityStatus,
    UserStatus,
    TaskStatus,
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
    "EntityStatus",
    "ErrorCode",
    "ErrorCodes",
    "ErrorContext",
    "ErrorMessages",
    "ExternalServiceError",
    "HandlerNotFoundError",
    "HttpStatus",
    "InfrastructureError",
    "InvalidCommandError",
    "InvalidQueryError",
    "OperationStatus",
    "QueryHandlerError",
    "RateLimitExceededError",
    "TaskStatus",
    "TransactionError",
    "UseCaseError",
    "UserStatus",
    "ValidationError",
    "ValidationStatus",
]
