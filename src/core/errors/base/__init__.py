"""Error hierarchy by architectural layer.

- Domain: Business rule violations, entity errors
- Application: Use case, command/query handler errors
- Infrastructure: Database, external service errors
"""

from core.errors.base.domain_errors import (
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
from core.errors.base.application_errors import (
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
from core.errors.base.infrastructure_errors import (
    InfrastructureError,
    DatabaseError,
    ExternalServiceError,
)

__all__ = [
    # Domain
    "AppException",
    "AuthenticationError",
    "AuthorizationError",
    "BusinessRuleViolationError",
    "ConflictError",
    "EntityNotFoundError",
    "ErrorContext",
    "RateLimitExceededError",
    "ValidationError",
    # Application
    "ApplicationError",
    "CommandHandlerError",
    "ConcurrencyError",
    "HandlerNotFoundError",
    "InvalidCommandError",
    "InvalidQueryError",
    "QueryHandlerError",
    "TransactionError",
    "UseCaseError",
    # Infrastructure
    "InfrastructureError",
    "DatabaseError",
    "ExternalServiceError",
]
