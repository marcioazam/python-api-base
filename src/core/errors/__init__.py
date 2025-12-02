"""Core error hierarchy.

Provides structured error handling:
- base/: Error hierarchy by layer (domain, application, infrastructure)
- http/: HTTP/API error handling (RFC 7807, handlers, constants)
- status: Operation status enums

**Feature: architecture-restructuring-2025**
"""

# Base error hierarchy
from core.errors.base import (
    # Domain
    AppException,
    AuthenticationError,
    AuthorizationError,
    BusinessRuleViolationError,
    ConflictError,
    EntityNotFoundError,
    ErrorContext,
    RateLimitExceededError,
    ValidationError,
    # Application
    ApplicationError,
    CommandHandlerError,
    ConcurrencyError,
    HandlerNotFoundError,
    InvalidCommandError,
    InvalidQueryError,
    QueryHandlerError,
    TransactionError,
    UseCaseError,
    # Infrastructure
    InfrastructureError,
    DatabaseError,
    ExternalServiceError,
)

# HTTP/API
from core.errors.http import (
    # Problem Details
    ProblemDetail,
    ValidationErrorDetail,
    PROBLEM_JSON_MEDIA_TYPE,
    # Exception Handlers
    setup_exception_handlers,
    http_exception_handler,
    validation_exception_handler,
    generic_exception_handler,
    # Constants
    HttpStatus,
    ErrorCode,
    ErrorCodes,
    ErrorMessages,
)

# Status enums
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
    # RFC 7807
    "ProblemDetail",
    "ValidationErrorDetail",
    "PROBLEM_JSON_MEDIA_TYPE",
    "setup_exception_handlers",
    "http_exception_handler",
    "validation_exception_handler",
    "generic_exception_handler",
]
