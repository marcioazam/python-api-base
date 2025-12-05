"""Validation error with structured field errors.

Used for input validation failures with detailed field-level error information.

**Feature: python-api-base-2025-state-of-art**
"""

from typing import Any

from application.common.errors.base.application_error import ApplicationError


class ValidationError(ApplicationError):
    """Validation error with structured field errors.

    Used for input validation failures with detailed
    field-level error information.

    Attributes:
        errors: List of field-level errors with structure:
                {"field": str, "message": str, "code": str}

    Example:
        >>> error = ValidationError(
        ...     message="Validation failed",
        ...     errors=[
        ...         {"field": "email", "message": "Invalid email format", "code": "invalid_email"},
        ...         {"field": "age", "message": "Must be >= 18", "code": "min_value"}
        ...     ]
        ... )
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
        """Return formatted error message with field details."""
        if self.errors:
            error_details = "; ".join(
                f"{e.get('field', 'unknown')}: {e.get('message', 'invalid')}"
                for e in self.errors
            )
            return f"{self.message}: {error_details}"
        return self.message
