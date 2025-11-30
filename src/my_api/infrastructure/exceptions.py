"""Infrastructure layer exceptions.

**Feature: infrastructure-code-review**
**Validates: Requirements 8.1, 8.2, 8.4**

This module defines a hierarchy of exceptions for the infrastructure layer,
providing consistent error handling across database, token store, telemetry,
and other infrastructure components.
"""

from typing import Any


class InfrastructureError(Exception):
    """Base exception for all infrastructure layer errors.
    
    All infrastructure-specific exceptions should inherit from this class
    to enable consistent error handling and logging.
    
    Attributes:
        message: Human-readable error message.
        details: Additional error context as key-value pairs.
    """

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize infrastructure error.
        
        Args:
            message: Human-readable error message.
            details: Additional error context.
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        """Return string representation with details."""
        if self.details:
            detail_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            return f"{self.message} ({detail_str})"
        return self.message


class DatabaseError(InfrastructureError):
    """Database-related errors.
    
    Raised when database operations fail, including connection errors,
    query failures, and transaction issues.
    """
    pass


class ConnectionPoolError(DatabaseError):
    """Connection pool specific errors.
    
    Raised when connection pool operations fail, such as exhausted
    connections or pool configuration issues.
    """
    pass


class TokenStoreError(InfrastructureError):
    """Token storage errors.
    
    Raised when token store operations fail, including storage,
    retrieval, and revocation failures.
    """
    pass


class TokenValidationError(TokenStoreError):
    """Token validation errors.
    
    Raised when token validation fails due to invalid format,
    expiration, or revocation.
    """
    pass


class TelemetryError(InfrastructureError):
    """Telemetry/tracing errors.
    
    Raised when telemetry operations fail, including span creation,
    metric recording, and exporter issues.
    """
    pass


class AuditLogError(InfrastructureError):
    """Audit logging errors.
    
    Raised when audit log operations fail, including logging
    and query failures.
    """
    pass


class ConfigurationError(InfrastructureError):
    """Configuration errors.
    
    Raised when infrastructure configuration is invalid or missing.
    """
    pass


class ExternalServiceError(InfrastructureError):
    """External service errors.
    
    Raised when communication with external services fails.
    
    Attributes:
        service_name: Name of the external service.
        retry_after: Suggested retry delay in seconds, if applicable.
    """

    def __init__(
        self,
        message: str,
        service_name: str,
        details: dict[str, Any] | None = None,
        retry_after: int | None = None,
    ) -> None:
        """Initialize external service error.
        
        Args:
            message: Human-readable error message.
            service_name: Name of the external service.
            details: Additional error context.
            retry_after: Suggested retry delay in seconds.
        """
        super().__init__(message, details)
        self.service_name = service_name
        self.retry_after = retry_after


class CacheError(InfrastructureError):
    """Cache-related errors.
    
    Raised when cache operations fail, including Redis
    connection and operation failures.
    """
    pass
