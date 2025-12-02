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
from core.errors.problem_details import (
    ProblemDetail,
    ValidationErrorDetail,
    PROBLEM_JSON_MEDIA_TYPE,
)
from core.errors.exception_handlers import (
    setup_exception_handlers,
    http_exception_handler,
    validation_exception_handler,
    generic_exception_handler,
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
