"""Infrastructure exception hierarchy.

**Feature: infrastructure-code-review**
**Validates: Requirements 8.2, 10.3**

Provides a structured exception hierarchy for consistent error handling
across all infrastructure modules.
"""

from __future__ import annotations

from typing import Any


class InfrastructureError(Exception):
    """Base exception for all infrastructure errors.

    All infrastructure exceptions should inherit from this class
    to enable consistent error handling and filtering.

    Attributes:
        message: Human-readable error message.
        details: Additional context about the error.
    """

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize infrastructure error.

        Args:
            message: Human-readable error message.
            details: Additional context about the error.
        """
        self.message = message
        self.details = details or {}
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        """Format message with details."""
        if not self.details:
            return self.message
        details_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
        return f"{self.message} ({details_str})"


class DatabaseError(InfrastructureError):
    """Database operation error.

    Raised when database operations fail due to connection issues,
    query errors, or constraint violations.
    """

    pass


class ConnectionPoolError(DatabaseError):
    """Connection pool error.

    Raised when connection pool operations fail, such as
    pool exhaustion or connection acquisition timeout.
    """

    pass


class TokenStoreError(InfrastructureError):
    """Token storage error.

    Raised when token storage operations fail.
    """

    pass


class TokenValidationError(TokenStoreError):
    """Token validation error.

    Raised when token validation fails due to invalid format,
    expiration, or signature verification failure.
    """

    pass


class TelemetryError(InfrastructureError):
    """Telemetry/observability error.

    Raised when telemetry operations fail, such as
    metric collection or trace export failures.
    """

    pass


class AuditLogError(InfrastructureError):
    """Audit logging error.

    Raised when audit log operations fail.
    """

    pass


class ConfigurationError(InfrastructureError):
    """Configuration error.

    Raised when configuration is invalid or missing.
    """

    pass


class ExternalServiceError(InfrastructureError):
    """External service error.

    Raised when external service calls fail.

    Attributes:
        service_name: Name of the external service.
        retry_after: Suggested retry delay in seconds.
    """

    def __init__(
        self,
        message: str,
        service_name: str | None = None,
        retry_after: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize external service error.

        Args:
            message: Human-readable error message.
            service_name: Name of the external service.
            retry_after: Suggested retry delay in seconds.
            details: Additional context about the error.
        """
        self.service_name = service_name
        self.retry_after = retry_after
        super().__init__(message, details)


class CacheError(InfrastructureError):
    """Cache operation error.

    Raised when cache operations fail.
    """

    pass


class MessagingError(InfrastructureError):
    """Messaging/queue error.

    Raised when messaging operations fail.
    """

    pass


class StorageError(InfrastructureError):
    """Storage operation error.

    Raised when file storage operations fail.
    """

    pass
