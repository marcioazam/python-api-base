"""Generic HTTP client with PEP 695 type parameters.

**Feature: enterprise-generics-2025**
**Requirement: R9 - Generic HTTP Client with Resilience**
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import timedelta
from enum import Enum
from typing import Any, Generic, TypeVar

import httpx
from pydantic import BaseModel, ValidationError as PydanticValidationError

logger = logging.getLogger(__name__)


# =============================================================================
# Error Types
# =============================================================================


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


# =============================================================================
# Configuration
# =============================================================================


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass(frozen=True, slots=True)
class RetryPolicy[TRequest]:
    """Retry policy configuration.

    **Requirement: R9.5 - Typed RetryPolicy[TRequest]**

    Type Parameters:
        TRequest: Request type this policy applies to.
    """

    max_retries: int = 3
    base_delay: timedelta = field(default_factory=lambda: timedelta(seconds=1))
    max_delay: timedelta = field(default_factory=lambda: timedelta(seconds=30))
    exponential_base: float = 2.0
    retry_on_status: frozenset[int] = field(
        default_factory=lambda: frozenset({429, 500, 502, 503, 504})
    )

    def get_delay(self, attempt: int) -> timedelta:
        """Calculate delay for retry attempt.

        Args:
            attempt: Current attempt number (0-based).

        Returns:
            Delay before next retry.
        """
        delay_seconds = self.base_delay.total_seconds() * (
            self.exponential_base ** attempt
        )
        return timedelta(seconds=min(delay_seconds, self.max_delay.total_seconds()))


@dataclass(frozen=True, slots=True)
class CircuitBreakerConfig:
    """Circuit breaker configuration."""

    failure_threshold: int = 5
    success_threshold: int = 3
    timeout: timedelta = field(default_factory=lambda: timedelta(seconds=30))


@dataclass
class HttpClientConfig:
    """HTTP client configuration.

    **Requirement: R9 - Client configuration**
    """

    base_url: str = ""
    timeout: timedelta = field(default_factory=lambda: timedelta(seconds=30))
    retry_policy: RetryPolicy[Any] = field(default_factory=RetryPolicy)
    circuit_breaker: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)
    headers: dict[str, str] = field(default_factory=dict)
    verify_ssl: bool = True


# =============================================================================
# Circuit Breaker
# =============================================================================


class CircuitBreaker:
    """Circuit breaker for HTTP client.

    **Requirement: R9.4 - CircuitBreaker[TRequest, TResponse]**
    """

    def __init__(self, config: CircuitBreakerConfig) -> None:
        self._config = config
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: float | None = None

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self._state

    @property
    def is_closed(self) -> bool:
        """Check if circuit allows requests."""
        if self._state == CircuitState.OPEN:
            # Check if timeout has passed
            if self._last_failure_time is not None:
                import time

                elapsed = time.time() - self._last_failure_time
                if elapsed >= self._config.timeout.total_seconds():
                    self._state = CircuitState.HALF_OPEN
                    return True
            return False
        return True

    def record_success(self) -> None:
        """Record successful request."""
        self._failure_count = 0
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self._config.success_threshold:
                self._state = CircuitState.CLOSED
                self._success_count = 0

    def record_failure(self) -> None:
        """Record failed request."""
        import time

        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._failure_count >= self._config.failure_threshold:
            self._state = CircuitState.OPEN
            self._success_count = 0


# =============================================================================
# Generic HTTP Client
# =============================================================================


class HttpClient[TRequest: BaseModel, TResponse: BaseModel]:
    """Generic HTTP client with typed request/response.

    **Requirement: R9.1 - Generic_Client[TRequest, TResponse]**
    **Requirement: R9.2 - Automatic serialization**

    Type Parameters:
        TRequest: Request model type (Pydantic BaseModel).
        TResponse: Response model type (Pydantic BaseModel).

    Example:
        ```python
        class CreateUserRequest(BaseModel):
            name: str
            email: str

        class UserResponse(BaseModel):
            id: str
            name: str
            email: str

        client = HttpClient[CreateUserRequest, UserResponse](
            config=HttpClientConfig(base_url="https://api.example.com"),
            response_type=UserResponse,
        )

        user = await client.post("/users", CreateUserRequest(name="John", email="john@example.com"))
        ```
    """

    def __init__(
        self,
        config: HttpClientConfig,
        response_type: type[TResponse],
    ) -> None:
        """Initialize HTTP client.

        Args:
            config: Client configuration.
            response_type: Expected response model type.
        """
        self._config = config
        self._response_type = response_type
        self._circuit_breaker = CircuitBreaker(config.circuit_breaker)
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "HttpClient[TRequest, TResponse]":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, *args) -> None:
        """Async context manager exit."""
        await self.close()

    async def connect(self) -> None:
        """Initialize HTTP client connection."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._config.base_url,
                timeout=self._config.timeout.total_seconds(),
                headers=self._config.headers,
                verify=self._config.verify_ssl,
            )

    async def close(self) -> None:
        """Close HTTP client connection."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def call(
        self,
        method: str,
        path: str,
        request: TRequest | None = None,
        **kwargs: Any,
    ) -> TResponse:
        """Make HTTP request with automatic serialization.

        **Requirement: R9.2 - call(request: TRequest) returns Awaitable[TResponse]**

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.).
            path: Request path.
            request: Optional request body model.
            **kwargs: Additional httpx request arguments.

        Returns:
            Parsed response model.

        Raises:
            TimeoutError: Request timed out.
            ValidationError: Response validation failed.
            CircuitBreakerError: Circuit breaker is open.
            HttpError: Other HTTP errors.
        """
        if not self._circuit_breaker.is_closed:
            raise CircuitBreakerError[TRequest](
                "Circuit breaker is open",
                request=request,
            )

        return await self._execute_with_retry(method, path, request, **kwargs)

    async def get(self, path: str, **kwargs: Any) -> TResponse:
        """Make GET request."""
        return await self.call("GET", path, **kwargs)

    async def post(self, path: str, request: TRequest, **kwargs: Any) -> TResponse:
        """Make POST request."""
        return await self.call("POST", path, request, **kwargs)

    async def put(self, path: str, request: TRequest, **kwargs: Any) -> TResponse:
        """Make PUT request."""
        return await self.call("PUT", path, request, **kwargs)

    async def patch(self, path: str, request: TRequest, **kwargs: Any) -> TResponse:
        """Make PATCH request."""
        return await self.call("PATCH", path, request, **kwargs)

    async def delete(self, path: str, **kwargs: Any) -> TResponse:
        """Make DELETE request."""
        return await self.call("DELETE", path, **kwargs)

    async def _execute_with_retry(
        self,
        method: str,
        path: str,
        request: TRequest | None,
        **kwargs: Any,
    ) -> TResponse:
        """Execute request with retry logic.

        **Requirement: R9.5 - Retry with exponential backoff**
        """
        policy = self._config.retry_policy
        last_error: Exception | None = None

        for attempt in range(policy.max_retries + 1):
            try:
                return await self._execute(method, path, request, **kwargs)
            except httpx.TimeoutException:
                raise TimeoutError(request, self._config.timeout)
            except httpx.HTTPStatusError as e:
                if e.response.status_code in policy.retry_on_status:
                    last_error = e
                    if attempt < policy.max_retries:
                        delay = policy.get_delay(attempt)
                        logger.warning(
                            f"Request failed with {e.response.status_code}, "
                            f"retrying in {delay.total_seconds()}s (attempt {attempt + 1})"
                        )
                        await asyncio.sleep(delay.total_seconds())
                        continue
                raise HttpError[TRequest](
                    str(e),
                    request=request,
                    status_code=e.response.status_code,
                    response_body=e.response.text,
                )

        # Should not reach here, but just in case
        if last_error:
            raise last_error
        raise HttpError[TRequest]("Max retries exceeded", request=request)

    async def _execute(
        self,
        method: str,
        path: str,
        request: TRequest | None,
        **kwargs: Any,
    ) -> TResponse:
        """Execute single HTTP request."""
        if self._client is None:
            await self.connect()

        # Serialize request
        json_body = None
        if request is not None:
            json_body = request.model_dump(mode="json")

        try:
            response = await self._client.request(
                method=method,
                url=path,
                json=json_body,
                **kwargs,
            )
            response.raise_for_status()

            self._circuit_breaker.record_success()

            # Parse response
            return self._parse_response(response.json())

        except (httpx.TimeoutException, httpx.HTTPStatusError):
            self._circuit_breaker.record_failure()
            raise

    def _parse_response(self, data: dict[str, Any]) -> TResponse:
        """Parse and validate response.

        **Requirement: R9.3 - Typed ValidationError[TResponse]**
        """
        try:
            return self._response_type.model_validate(data)
        except PydanticValidationError as e:
            raise ValidationError[TResponse](
                f"Response validation failed: {e}",
                response_type=self._response_type,
                raw_response=data,
                validation_errors=e.errors(),
            )

    @property
    def circuit_state(self) -> CircuitState:
        """Get current circuit breaker state."""
        return self._circuit_breaker.state
