"""Tests for resilience middleware module.

Tests for ResilienceMiddleware class.
"""

import pytest

from application.common.middleware.resilience.circuit_breaker import (
    CircuitBreakerConfig,
    CircuitState,
)
from application.common.middleware.resilience.resilience import ResilienceMiddleware
from application.common.middleware.resilience.retry import RetryConfig


class TestResilienceMiddleware:
    """Tests for ResilienceMiddleware class."""

    def test_init_default_configs(self) -> None:
        """Middleware should use default configs if not provided."""
        middleware = ResilienceMiddleware()
        assert middleware._retry is not None
        assert middleware._circuit_breaker is not None

    def test_init_custom_retry_config(self) -> None:
        """Middleware should accept custom retry config."""
        retry_config = RetryConfig(max_retries=5)
        middleware = ResilienceMiddleware(retry_config=retry_config)
        assert middleware._retry._config.max_retries == 5

    def test_init_custom_circuit_config(self) -> None:
        """Middleware should accept custom circuit breaker config."""
        circuit_config = CircuitBreakerConfig(failure_threshold=10)
        middleware = ResilienceMiddleware(circuit_config=circuit_config)
        assert middleware._circuit_breaker._config.failure_threshold == 10

    def test_circuit_state_property(self) -> None:
        """circuit_state should return current circuit breaker state."""
        middleware = ResilienceMiddleware()
        assert middleware.circuit_state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_call_success(self) -> None:
        """Middleware should pass through successful calls."""
        middleware = ResilienceMiddleware()

        async def handler(cmd: str) -> str:
            return f"handled: {cmd}"

        result = await middleware("test", handler)
        assert result == "handled: test"

    @pytest.mark.asyncio
    async def test_call_with_retry_on_failure(self) -> None:
        """Middleware should retry on transient failures."""
        # Use TimeoutError which is retryable by default
        retry_config = RetryConfig(max_retries=3, base_delay=0.001)
        middleware = ResilienceMiddleware(retry_config=retry_config)
        call_count = 0

        async def flaky_handler(cmd: str) -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise TimeoutError("transient error")
            return "success"

        result = await middleware("test", flaky_handler)
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_call_preserves_result(self) -> None:
        """Middleware should preserve complex results."""
        middleware = ResilienceMiddleware()

        async def handler(cmd: str) -> dict:
            return {"status": "ok", "data": cmd}

        result = await middleware("test", handler)
        assert result == {"status": "ok", "data": "test"}

    @pytest.mark.asyncio
    async def test_call_propagates_exception_after_retries(self) -> None:
        """Middleware should propagate exception after max retries."""
        retry_config = RetryConfig(max_retries=2, base_delay=0.001)
        middleware = ResilienceMiddleware(retry_config=retry_config)

        async def failing_handler(cmd: str) -> str:
            raise RuntimeError("permanent error")

        with pytest.raises(RuntimeError, match="permanent error"):
            await middleware("test", failing_handler)

    @pytest.mark.asyncio
    async def test_call_chains_circuit_breaker_and_retry(self) -> None:
        """Middleware should chain circuit breaker and retry correctly."""
        retry_config = RetryConfig(max_retries=2, base_delay=0.001)
        circuit_config = CircuitBreakerConfig(failure_threshold=5)
        middleware = ResilienceMiddleware(
            retry_config=retry_config, circuit_config=circuit_config
        )

        async def handler(cmd: str) -> str:
            return "ok"

        result = await middleware("test", handler)
        assert result == "ok"
        # Circuit should still be closed after success
        assert middleware.circuit_state == CircuitState.CLOSED
