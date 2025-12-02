"""Unit tests for circuit breaker.

**Feature: enterprise-infrastructure-2025**
**Requirement: R1.5 - Circuit breaker pattern**
"""

import pytest
import asyncio

from infrastructure.redis.circuit_breaker import (
    CircuitBreaker,
    CircuitState,
    CircuitOpenError,
)


class TestCircuitBreaker:
    """Tests for CircuitBreaker."""

    @pytest.fixture
    def breaker(self) -> CircuitBreaker:
        """Create circuit breaker for testing."""
        return CircuitBreaker(
            failure_threshold=3,
            reset_timeout=1.0,
            half_open_max_calls=1,
        )

    @pytest.mark.asyncio
    async def test_initial_state_closed(self, breaker: CircuitBreaker) -> None:
        """Test initial state is closed."""
        assert breaker.state == CircuitState.CLOSED
        assert breaker.is_closed
        assert not breaker.is_open

    @pytest.mark.asyncio
    async def test_can_execute_when_closed(self, breaker: CircuitBreaker) -> None:
        """Test can execute when closed."""
        assert await breaker.can_execute()

    @pytest.mark.asyncio
    async def test_opens_after_threshold(self, breaker: CircuitBreaker) -> None:
        """Test circuit opens after failure threshold."""
        # Record failures up to threshold
        for _ in range(3):
            await breaker.record_failure()

        assert breaker.state == CircuitState.OPEN
        assert not await breaker.can_execute()

    @pytest.mark.asyncio
    async def test_success_resets_count(self, breaker: CircuitBreaker) -> None:
        """Test success resets failure count."""
        await breaker.record_failure()
        await breaker.record_failure()
        await breaker.record_success()

        # Should be able to fail again without opening
        await breaker.record_failure()
        await breaker.record_failure()

        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_half_open_after_timeout(self, breaker: CircuitBreaker) -> None:
        """Test transitions to half-open after timeout."""
        # Open the circuit
        for _ in range(3):
            await breaker.record_failure()

        assert breaker.state == CircuitState.OPEN

        # Wait for timeout
        await asyncio.sleep(1.1)

        # Should transition to half-open
        assert await breaker.can_execute()
        assert breaker.state == CircuitState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_closes_after_half_open_success(self, breaker: CircuitBreaker) -> None:
        """Test closes after successful half-open call."""
        # Open then wait for half-open
        for _ in range(3):
            await breaker.record_failure()

        await asyncio.sleep(1.1)
        await breaker.can_execute()  # Transitions to half-open

        await breaker.record_success()

        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_reopens_after_half_open_failure(self, breaker: CircuitBreaker) -> None:
        """Test reopens after half-open failure."""
        # Open then wait for half-open
        for _ in range(3):
            await breaker.record_failure()

        await asyncio.sleep(1.1)
        await breaker.can_execute()  # Transitions to half-open

        await breaker.record_failure()

        assert breaker.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_manual_reset(self, breaker: CircuitBreaker) -> None:
        """Test manual reset."""
        # Open the circuit
        for _ in range(3):
            await breaker.record_failure()

        assert breaker.state == CircuitState.OPEN

        await breaker.reset()

        assert breaker.state == CircuitState.CLOSED


class TestCircuitOpenError:
    """Tests for CircuitOpenError."""

    def test_default_message(self) -> None:
        """Test default error message."""
        error = CircuitOpenError()
        assert "open" in str(error).lower()

    def test_custom_message(self) -> None:
        """Test custom error message."""
        error = CircuitOpenError("Redis circuit open")
        assert "Redis" in str(error)
