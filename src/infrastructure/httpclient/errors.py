"""HTTP client error types with generic type parameters.

**Feature: enterprise-generics-2025**
**Requirement: R9.6 - Typed errors with request/response context**
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any


class HttpError[TRequest](Exception):
    """Base HTTP error with request context.

    Type Parameters:
        TRequest: Request type that caused the error.

    **Requirement: R9.6 - Typed errors with request context**
    """

    def __init__(
        self,
        message: str,
        request: TRequest | None = None,
        status_code: int | None = None,
        response_body: str | None = None,
    ) -> None:
        super().__init__(message)
        self.request = request
        self.status_code = status_code
        self.response_body = response_body


class TimeoutError[TRequest](HttpError[TRequest]):
    """Timeout error with request context.

    **Requirement: R9.6 - Typed TimeoutError[TRequest]**
    """

    def __init__(
        self,
        request: TRequest,
        timeout: timedelta,
    ) -> None:
        super().__init__(
            f"Request timed out after {timeout.total_seconds()}s",
            request=request,
        )
        self.timeout = timeout


class ValidationError[TResponse](Exception):
    """Response validation error.

    **Requirement: R9.3 - Typed ValidationError[TResponse]**
    """

    def __init__(
        self,
        message: str,
        response_type: type[TResponse],
        raw_response: dict[str, Any],
        validation_errors: list[dict[str, Any]],
    ) -> None:
        super().__init__(message)
        self.response_type = response_type
        self.raw_response = raw_response
        self.validation_errors = validation_errors


class CircuitBreakerError[TRequest](HttpError[TRequest]):
    """Circuit breaker is open error.

    **Requirement: R9.4 - Circuit breaker integration**
    """

    pass
