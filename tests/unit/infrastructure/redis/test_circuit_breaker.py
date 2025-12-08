"""Tests for Redis circuit breaker module.

Tests for CircuitBreaker, CircuitState, and CircuitOpenError.
"""

import asyncio
import time
from unittest.mock import patch

import pytest

from infrastructure.redis.circuit_breaker import (
    CircuitBreaker,
    CircuitOpenError,
    CircuitState,
)


class TestCircuitState:
    """Tests for CircuitState enum."""

    def test_closed_value(self) -> None:
        """CLOSED should have correct value."""
        assert CircuitState.CLOSED.value == "closed"

    def test_open_value(self) -> None:
        """OPEN should have correct value."""
        assert CircuitState.OPEN.value == "open"

    def test_half_open_value(self) -> None:
        """HALF_OPEN should have correct value."""
        assert CircuitState.HALF_OPEN.value == "half_open"


class TestCircuitBreaker:
    """Tests for CircuitBreaker class."""

    def test_default_failure_threshold(self) -> None:
        """Default failure threshold should be 5."""
        cb = CircuitBreaker()
        assert cb.failure_threshold == 5

    def test_default_reset_timeout(self) -> None:
        """Default reset timeout should be 30 seconds."""
        cb = CircuitBreaker()
        assert cb.reset_timeout == 30.0

    def test_default_half_open_max_calls(self) -> None:
        """Default half_open_max_calls should be 1."""
        cb = CircuitBreaker()
        assert cb.half_open_max_calls == 1

    def test_custom_parameters(self) -> None:
        """Should accept custom parameters."""
        cb = CircuitBreaker(
            failure_threshold=10,
            reset_timeout=60.0,
            half_open_max_calls=3,
        )
        assert cb.failure_threshold == 10
        assert cb.reset_timeout == 60.0
        assert cb.half_open_max_calls == 3

    def test_initial_state_is_closed(self) -> None:
        """Initial state should be CLOSED."""
        cb = CircuitBreaker()
        assert cb.state == CircuitState.CLOSED

    def test_is_closed_property(self) -> None:
        """is_closed should return True when closed."""
        cb = CircuitBreaker()
        assert cb.is_closed is True

    def test_is_open_property_when_closed(self) -> None:
        """is_open should return False when closed."""
        cb = CircuitBreaker()
        assert cb.is_open is False

    @pytest.mark.asyncio
    async def test_can_execute_when_closed(self) -> None:
        """can_execute should return True when closed."""
        cb = CircuitBreaker()
        assert await cb.can_execute() is True

    @pytest.mark.asyncio
    async def test_record_success_resets_failure_count(self) -> None:
        """record_success should reset failure count."""
        cb = CircuitBreaker()
        cb._failure_count = 3
        await cb.record_success()
        assert cb._failure_count == 0

    @pytest.mark.asyncio
    async def test_record_failure_increments_count(self) -> None:
        """record_failure should increment failure count."""
        cb = CircuitBreaker()
        await cb.record_failure()
        assert cb._failure_count == 1

    @pytest.mark.asyncio
    async def test_opens_after_threshold(self) -> None:
        """Circuit should open after failure threshold."""
        cb = CircuitBreaker(failure_threshold=3)
        for _ in range(3):
            await cb.record_failure()
        assert cb.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_can_execute_returns_false_when_open(self) -> None:
        """can_execute should return False when open."""
        cb = CircuitBreaker(failure_threshold=1)
        await cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert await cb.can_execute() is False

    @pytest.mark.asyncio
    async def test_transitions_to_half_open_after_timeout(self) -> None:
        """Circuit should transition to HALF_OPEN after timeout."""
        cb = CircuitBreaker(failure_threshold=1, reset_timeout=0.1)
        await cb.record_failure()
        assert cb.state == CircuitState.OPEN

        await asyncio.sleep(0.15)
        assert await cb.can_execute() is True
        assert cb.state == CircuitState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_half_open_state_after_timeout(self) -> None:
        """Circuit should transition to HALF_OPEN after timeout."""
        cb = CircuitBreaker(failure_threshold=1, reset_timeout=0.01, half_open_max_calls=1)
        await cb.record_failure()
        assert cb.state == CircuitState.OPEN

        await asyncio.sleep(0.02)
        # Calling can_execute transitions to HALF_OPEN
        result = await cb.can_execute()
        assert result is True
        assert cb.state == CircuitState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_closes_after_success_in_half_open(self) -> None:
        """Circuit should close after success in HALF_OPEN."""
        cb = CircuitBreaker(failure_threshold=1, reset_timeout=0.01)
        await cb.record_failure()
        await asyncio.sleep(0.02)
        await cb.can_execute()  # Transition to HALF_OPEN

        await cb.record_success()
        assert cb.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_reopens_after_failure_in_half_open(self) -> None:
        """Circuit should reopen after failure in HALF_OPEN."""
        cb = CircuitBreaker(failure_threshold=1, reset_timeout=0.01)
        await cb.record_failure()
        await asyncio.sleep(0.02)
        await cb.can_execute()  # Transition to HALF_OPEN

        await cb.record_failure()
        assert cb.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_reset_closes_circuit(self) -> None:
        """reset should close circuit and clear state."""
        cb = CircuitBreaker(failure_threshold=1)
        await cb.record_failure()
        assert cb.state == CircuitState.OPEN

        await cb.reset()
        assert cb.state == CircuitState.CLOSED
        assert cb._failure_count == 0
        assert cb._half_open_calls == 0

    @pytest.mark.asyncio
    async def test_record_failure_with_error(self) -> None:
        """record_failure should accept error parameter."""
        cb = CircuitBreaker(failure_threshold=1)
        error = ValueError("test error")
        await cb.record_failure(error)
        assert cb.state == CircuitState.OPEN


class TestCircuitOpenError:
    """Tests for CircuitOpenError exception."""

    def test_default_message(self) -> None:
        """Should have default message."""
        error = CircuitOpenError()
        assert str(error) == "Circuit breaker is open"

    def test_custom_message(self) -> None:
        """Should accept custom message."""
        error = CircuitOpenError("Custom message")
        assert str(error) == "Custom message"

    def test_is_exception(self) -> None:
        """Should be an Exception."""
        error = CircuitOpenError()
        assert isinstance(error, Exception)

    def test_can_be_raised(self) -> None:
        """Should be raisable."""
        with pytest.raises(CircuitOpenError):
            raise CircuitOpenError()
