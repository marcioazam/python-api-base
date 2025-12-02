"""Application exception hierarchy.

**Feature: core-code-review, ultimate-generics-code-review-2025**
**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5**
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from core.shared.utils.ids import generate_ulid

from core.errors.constants import ErrorCodes, ErrorMessages, HttpStatus

__all__ = [
    "AppException",
    "AuthenticationError",
    "AuthorizationError",
    "BusinessRuleViolationError",
    "ConflictError",
    "EntityNotFoundError",
    "ErrorContext",
    "RateLimitExceededError",
    "ValidationError",
]


@dataclass(frozen=True, slots=True)
class ErrorContext:
    """Immutable error context for request tracing.

    **Feature: core-code-review, deep-code-quality-generics-review**
    **Validates: Requirements 2.1, 8.1, 12.1, 14.6**

    Uses slots=True for memory optimization (20% reduction per Real Python benchmarks).

    Attributes:
        correlation_id: Unique identifier for request tracing.
        timestamp: When the error occurred.
        request_path: Optional request path where error occurred.
    """

    correlation_id: str = field(default_factory=generate_ulid)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    request_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert context to dictionary."""
        return {
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp.isoformat(),
            "request_path": self.request_path,
        }


class AppException(Exception):
    """Base application exception with tracing support.

    All application-specific exceptions should inherit from this class.
    Provides structured error information for consistent error handling.

    **Feature: core-code-review, Property 3: Exception Serialization Consistency**
    **Validates: Requirements 2.1, 2.2**
    """

    def __init__(
        self,
        message: str,
        error_code: str,
        status_code: int = 400,
        details: dict[str, Any] | None = None,
        context: ErrorContext | None = None,
    ) -> None:
        """Initialize application exception.

        Args:
            message: Human-readable error message.
            error_code: Machine-readable error code.
            status_code: HTTP status code.
            details: Additional error details.
            context: Error context for tracing.
        """
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        self.context = context or ErrorContext()
        super().__init__(message)

    @property
    def correlation_id(self) -> str:
        """Get correlation ID for request tracing."""
        return self.context.correlation_id

    @property
    def timestamp(self) -> datetime:
        """Get timestamp when error occurred."""
        return self.context.timestamp

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for serialization.

        **Feature: core-code-review, Property 3: Exception Serialization Consistency**
        **Validates: Requirements 2.2**

        Returns:
            dict: Exception data as dictionary with consistent structure.
        """
        result = {
            "message": self.message,
            "error_code": self.error_code,
            "status_code": self.status_code,
            "details": self.details,
            "correlation_id": self.context.correlation_id,
            "timestamp": self.context.timestamp.isoformat(),
        }

        # Include cause chain if present
        if self.__cause__:
            if isinstance(self.__cause__, AppException):
                result["cause"] = self.__cause__.to_dict()
            else:
                result["cause"] = {
                    "type": type(self.__cause__).__name__,
                    "message": str(self.__cause__),
                }

        return result


class EntityNotFoundError(AppException):
    """Raised when an entity is not found."""

    def __init__(self, entity_type: str, entity_id: str | int) -> None:
        """Initialize entity not found error.

        Args:
            entity_type: Type/name of the entity.
            entity_id: ID of the entity that was not found.
        """
        super().__init__(
            message=ErrorMessages.ENTITY_NOT_FOUND.format(
                entity_type=entity_type, entity_id=entity_id
            ),
            error_code=ErrorCodes.ENTITY_NOT_FOUND,
            status_code=HttpStatus.NOT_FOUND,
            details={"entity_type": entity_type, "entity_id": str(entity_id)},
        )


class ValidationError(AppException):
    """Raised when validation fails.

    **Feature: core-code-review, ultimate-generics-code-review-2025**
    **Validates: Requirements 2.3**
    """

    def __init__(
        self,
        errors: list[dict[str, Any]] | dict[str, Any],
        message: str | None = None,
        context: ErrorContext | None = None,
    ) -> None:
        """Initialize validation error.

        Args:
            errors: Validation errors - can be list or dict format.
            message: Overall error message. Defaults to ErrorMessages.VALIDATION_FAILED.
            context: Error context for tracing.
        """
        # Normalize errors to list format for consistency
        if isinstance(errors, dict):
            normalized_errors = [
                {"field": field, "message": msg} for field, msg in errors.items()
            ]
        else:
            normalized_errors = errors

        super().__init__(
            message=message or ErrorMessages.VALIDATION_FAILED,
            error_code=ErrorCodes.VALIDATION_ERROR,
            status_code=HttpStatus.UNPROCESSABLE_ENTITY,
            details={"errors": normalized_errors},
            context=context,
        )


class BusinessRuleViolationError(AppException):
    """Raised when a business rule is violated."""

    def __init__(self, rule: str, message: str) -> None:
        """Initialize business rule violation error.

        Args:
            rule: Name/identifier of the violated rule.
            message: Description of the violation.
        """
        super().__init__(
            message=ErrorMessages.BUSINESS_RULE_VIOLATED.format(
                rule=rule, message=message
            ),
            error_code=f"{ErrorCodes.BUSINESS_RULE_VIOLATION}_{rule.upper()}",
            status_code=HttpStatus.BAD_REQUEST,
            details={"rule": rule},
        )


class AuthenticationError(AppException):
    """Raised when authentication fails."""

    def __init__(
        self,
        message: str | None = None,
        scheme: str = "Bearer",
    ) -> None:
        """Initialize authentication error.

        Args:
            message: Error message. Defaults to ErrorMessages.AUTHENTICATION_REQUIRED.
            scheme: Authentication scheme for WWW-Authenticate header.
        """
        super().__init__(
            message=message or ErrorMessages.AUTHENTICATION_REQUIRED,
            error_code=ErrorCodes.AUTHENTICATION_ERROR,
            status_code=HttpStatus.UNAUTHORIZED,
            details={"scheme": scheme},
        )


class AuthorizationError(AppException):
    """Raised when authorization fails."""

    def __init__(
        self,
        message: str | None = None,
        required_permission: str | None = None,
    ) -> None:
        """Initialize authorization error.

        Args:
            message: Error message. Defaults to ErrorMessages.PERMISSION_DENIED.
            required_permission: The permission that was required.
        """
        details = {}
        if required_permission:
            details["required_permission"] = required_permission
            msg = ErrorMessages.PERMISSION_REQUIRED.format(
                permission=required_permission
            )
        else:
            msg = message or ErrorMessages.PERMISSION_DENIED

        super().__init__(
            message=msg,
            error_code=ErrorCodes.AUTHORIZATION_ERROR,
            status_code=HttpStatus.FORBIDDEN,
            details=details,
        )


class RateLimitExceededError(AppException):
    """Raised when rate limit is exceeded."""

    def __init__(
        self,
        retry_after: int,
        message: str | None = None,
    ) -> None:
        """Initialize rate limit exceeded error.

        Args:
            retry_after: Seconds until the client can retry.
            message: Error message. Defaults to ErrorMessages.RATE_LIMIT_EXCEEDED.
        """
        super().__init__(
            message=message
            or ErrorMessages.RATE_LIMIT_EXCEEDED.format(retry_after=retry_after),
            error_code=ErrorCodes.RATE_LIMIT_EXCEEDED,
            status_code=HttpStatus.TOO_MANY_REQUESTS,
            details={"retry_after": retry_after},
        )


class ConflictError(AppException):
    """Raised when there is a resource conflict."""

    def __init__(
        self,
        message: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
    ) -> None:
        """Initialize conflict error.

        Args:
            message: Error message. Auto-generated if resource_type and resource_id provided.
            resource_type: Type of the conflicting resource.
            resource_id: ID of the conflicting resource.
        """
        details = {}
        if resource_type:
            details["resource_type"] = resource_type
        if resource_id:
            details["resource_id"] = resource_id

        if message is None and resource_type and resource_id:
            message = ErrorMessages.CONFLICT_RESOURCE.format(
                resource_type=resource_type, resource_id=resource_id
            )
        elif message is None:
            message = "Resource conflict"

        super().__init__(
            message=message,
            error_code=ErrorCodes.CONFLICT,
            status_code=HttpStatus.CONFLICT,
            details=details,
        )
