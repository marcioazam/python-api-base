"""Common exceptions for CQRS infrastructure.

Provides unified exception types for the application layer:
- HandlerNotFoundError: No handler registered for command/query
- ValidationError: Input validation failed
- ApplicationError: Base for application-level errors

**Feature: python-api-base-2025-state-of-art**
**Validates: Requirements 2.1, 2.2**
"""

from typing import Any


class ApplicationError(Exception):
    """Base exception for application-level errors.

    Provides structured error information with error codes
    for consistent error handling across the application.
    """

    def __init__(
        self,
        message: str,
        code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize application error.

        Args:
            message: Human-readable error message.
            code: Machine-readable error code.
            details: Additional error context.
        """
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(message)


class HandlerNotFoundError(ApplicationError):
    """Raised when no handler is registered for a command/query type."""

    def __init__(self, handler_type: type) -> None:
        self.handler_type = handler_type
        super().__init__(
            message=f"No handler registered for {handler_type.__name__}",
            code="HANDLER_NOT_FOUND",
            details={"handler_type": handler_type.__name__},
        )


class ValidationError(ApplicationError):
    """Validation error with structured field errors.

    Used for input validation failures with detailed
    field-level error information.
    """

    def __init__(
        self,
        message: str,
        errors: list[dict[str, Any]] | None = None,
    ) -> None:
        """Initialize validation error.

        Args:
            message: Error message summary.
            errors: List of field-level errors with structure:
                    {"field": str, "message": str, "code": str}
        """
        self.errors = errors or []
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            details={"errors": self.errors},
        )

    def __str__(self) -> str:
        if self.errors:
            error_details = "; ".join(
                f"{e.get('field', 'unknown')}: {e.get('message', 'invalid')}"
                for e in self.errors
            )
            return f"{self.message}: {error_details}"
        return self.message


class NotFoundError(ApplicationError):
    """Entity not found error."""

    def __init__(self, entity_type: str, entity_id: Any) -> None:
        """Initialize not found error.

        Args:
            entity_type: Type of entity.
            entity_id: Entity identifier.
        """
        self.entity_type = entity_type
        self.entity_id = entity_id
        super().__init__(
            message=f"{entity_type} with id '{entity_id}' not found",
            code="NOT_FOUND",
            details={"entity_type": entity_type, "entity_id": str(entity_id)},
        )


class ConflictError(ApplicationError):
    """Resource conflict error (e.g., duplicate key)."""

    def __init__(self, message: str, resource: str | None = None) -> None:
        super().__init__(
            message=message,
            code="CONFLICT",
            details={"resource": resource} if resource else {},
        )


class UnauthorizedError(ApplicationError):
    """Authentication required error."""

    def __init__(self, message: str = "Authentication required") -> None:
        super().__init__(message=message, code="UNAUTHORIZED")


class ForbiddenError(ApplicationError):
    """Access denied error."""

    def __init__(self, message: str = "Access denied") -> None:
        super().__init__(message=message, code="FORBIDDEN")
