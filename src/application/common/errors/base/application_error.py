"""Base application error class.

Provides structured error information with error codes for consistent error handling.

**Feature: python-api-base-2025-state-of-art**
"""

from typing import Any


class ApplicationError(Exception):
    """Base exception for application-level errors.

    Provides structured error information with error codes
    for consistent error handling across the application.

    Attributes:
        message: Human-readable error message.
        code: Machine-readable error code.
        details: Additional error context as dictionary.

    Example:
        >>> error = ApplicationError(
        ...     message="Operation failed",
        ...     code="OPERATION_FAILED",
        ...     details={"operation": "create_user"}
        ... )
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
