"""External service infrastructure exceptions.

**Feature: infrastructure-code-review**
**Validates: Requirements 8.2, 10.3**
"""

from __future__ import annotations

from typing import Any

from infrastructure.errors.base import InfrastructureError


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
