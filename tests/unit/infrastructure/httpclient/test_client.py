"""Unit tests for generic HTTP client.

**Feature: enterprise-generics-2025**
**Requirement: R9 - Generic HTTP Client**
"""

import pytest
from datetime import timedelta
from unittest.mock import AsyncMock, patch, MagicMock

from pydantic import BaseModel

from infrastructure.httpclient.client import (
    HttpClient,
    HttpClientConfig,
    HttpError,
    TimeoutError,
    ValidationError,
    RetryPolicy,
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
)


# =============================================================================
# Test Models
# =============================================================================


class CreateUserRequest(BaseModel):
    """Test request model."""

    name: str
    email: str


class UserResponse(BaseModel):
    """Test response model."""

    id: str
    name: str
    email: str


# =============================================================================
# Tests
# =============================================================================


class TestRetryPolicy:
    """Tests for RetryPolicy."""

    def test_default_policy(self) -> None:
        """Test default retry policy."""
        policy = RetryPolicy[CreateUserRequest]()

        assert policy.max_retries == 3
        assert policy.base_delay == timedelta(seconds=1)

    def test_get_delay_exponential(self) -> None:
        """Test exponential backoff delay calculation."""
        policy = RetryPolicy[CreateUserRequest](
            base_delay=timedelta(seconds=1),
            exponential_base=2.0,
        )

        assert policy.get_delay(0) == timedelta(seconds=1)
        assert policy.get_delay(1) == timedelta(seconds=2)
        assert policy.get_delay(2) == timedelta(seconds=4)

    def test_get_delay_max_cap(self) -> None:
        """Test delay is capped at max_delay."""
        policy = RetryPolicy[CreateUserRequest](
            base_delay=timedelta(seconds=10),
            max_delay=timedelta(seconds=30),
            exponential_base=2.0,
        )

        # 10 * 2^3 = 80, capped at 30
        assert policy.get_delay(3) == timedelta(seconds=30)


class TestCircuitBreaker:
    """Tests for CircuitBreaker."""

    @pytest.fixture
    def config(self) -> CircuitBreakerConfig:
        """Create test config."""
        return CircuitBreakerConfig(
            failure_threshold=3,
            success_threshold=2,
            timeout=timedelta(seconds=1),
        )

    @pytest.fixture
    def breaker(self, config: CircuitBreakerConfig) -> CircuitBreaker:
        """Create test circuit breaker."""
        return CircuitBreaker(config)

    def test_initial_state_closed(self, breaker: CircuitBreaker) -> None:
        """Test initial state is closed."""
        assert breaker.state == CircuitState.CLOSED
        assert breaker.is_closed

    def test_opens_after_threshold(self, breaker: CircuitBreaker) -> None:
        """Test circuit opens after failure threshold."""
        for _ in range(3):
            breaker.record_failure()

        assert breaker.state == CircuitState.OPEN
        assert not breaker.is_closed

    def test_success_resets_failure_count(self, breaker: CircuitBreaker) -> None:
        """Test success resets failure count."""
        breaker.record_failure()
        breaker.record_failure()
        breaker.record_success()  # Reset
        breaker.record_failure()  # Only 1 failure now

        assert breaker.state == CircuitState.CLOSED

    def test_half_open_after_timeout(self, breaker: CircuitBreaker) -> None:
        """Test circuit goes half-open after timeout."""
        import time

        # Open the circuit
        for _ in range(3):
            breaker.record_failure()

        assert breaker.state == CircuitState.OPEN

        # Wait for timeout
        time.sleep(1.1)

        # Should be half-open now
        assert breaker.is_closed  # is_closed checks and transitions
        assert breaker.state == CircuitState.HALF_OPEN

    def test_closes_after_success_threshold(self, breaker: CircuitBreaker) -> None:
        """Test circuit closes after success threshold in half-open."""
        import time

        # Open and wait for half-open
        for _ in range(3):
            breaker.record_failure()
        time.sleep(1.1)
        breaker.is_closed  # Trigger transition to half-open

        # Record successes
        breaker.record_success()
        breaker.record_success()

        assert breaker.state == CircuitState.CLOSED


class TestHttpClientConfig:
    """Tests for HttpClientConfig."""

    def test_default_config(self) -> None:
        """Test default configuration."""
        config = HttpClientConfig()

        assert config.base_url == ""
        assert config.timeout == timedelta(seconds=30)
        assert config.verify_ssl is True

    def test_custom_config(self) -> None:
        """Test custom configuration."""
        config = HttpClientConfig(
            base_url="https://api.example.com",
            timeout=timedelta(seconds=60),
            headers={"Authorization": "Bearer token"},
        )

        assert config.base_url == "https://api.example.com"
        assert config.timeout == timedelta(seconds=60)
        assert config.headers["Authorization"] == "Bearer token"


class TestHttpClientTypes:
    """Tests for generic type parameters."""

    def test_client_type_parameters(self) -> None:
        """Test client can be instantiated with type parameters."""
        config = HttpClientConfig()
        client: HttpClient[CreateUserRequest, UserResponse] = HttpClient(
            config=config,
            response_type=UserResponse,
        )

        assert client._response_type == UserResponse

    def test_error_type_parameters(self) -> None:
        """Test error types preserve request type."""
        request = CreateUserRequest(name="John", email="john@example.com")
        error = HttpError[CreateUserRequest](
            "Test error",
            request=request,
            status_code=500,
        )

        assert error.request == request
        assert error.status_code == 500

    def test_timeout_error_type(self) -> None:
        """Test timeout error with request context."""
        request = CreateUserRequest(name="John", email="john@example.com")
        error = TimeoutError[CreateUserRequest](
            request=request,
            timeout=timedelta(seconds=30),
        )

        assert error.request == request
        assert error.timeout == timedelta(seconds=30)

    def test_validation_error_type(self) -> None:
        """Test validation error with response type."""
        error = ValidationError[UserResponse](
            message="Validation failed",
            response_type=UserResponse,
            raw_response={"invalid": "data"},
            validation_errors=[{"loc": ["id"], "msg": "field required"}],
        )

        assert error.response_type == UserResponse
        assert len(error.validation_errors) == 1


class TestHttpClientIntegration:
    """Integration-style tests for HttpClient."""

    @pytest.fixture
    def config(self) -> HttpClientConfig:
        """Create test config."""
        return HttpClientConfig(
            base_url="https://api.example.com",
            timeout=timedelta(seconds=5),
        )

    @pytest.mark.asyncio
    async def test_parse_response(self, config: HttpClientConfig) -> None:
        """Test response parsing."""
        client: HttpClient[CreateUserRequest, UserResponse] = HttpClient(
            config=config,
            response_type=UserResponse,
        )

        response = client._parse_response({
            "id": "123",
            "name": "John",
            "email": "john@example.com",
        })

        assert response.id == "123"
        assert response.name == "John"
        assert isinstance(response, UserResponse)

    @pytest.mark.asyncio
    async def test_parse_response_validation_error(
        self,
        config: HttpClientConfig,
    ) -> None:
        """Test response parsing raises ValidationError on invalid data."""
        client: HttpClient[CreateUserRequest, UserResponse] = HttpClient(
            config=config,
            response_type=UserResponse,
        )

        with pytest.raises(ValidationError) as exc_info:
            client._parse_response({"invalid": "data"})

        assert exc_info.value.response_type == UserResponse

    @pytest.mark.asyncio
    async def test_context_manager(self, config: HttpClientConfig) -> None:
        """Test async context manager."""
        async with HttpClient[CreateUserRequest, UserResponse](
            config=config,
            response_type=UserResponse,
        ) as client:
            assert client._client is not None

        assert client._client is None
