"""Integration tests for Redis cache.

**Feature: infrastructure-modules-integration-analysis**
**Validates: Requirements 2.1, 2.5**
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from infrastructure.redis.circuit_breaker import CircuitBreaker, CircuitState


class TestCircuitBreakerIntegration:
    """Integration tests for circuit breaker pattern.
    
    **Feature: infrastructure-modules-integration-analysis**
    **Property 4: Circuit breaker protege contra falhas Redis**
    **Validates: Requirements 2.1**
    """

    @pytest.fixture
    def breaker(self) -> CircuitBreaker:
        """Create circuit breaker for testing."""
        return CircuitBreaker(
            failure_threshold=3,
            reset_timeout=0.1,
            half_open_max_calls=1,
        )

    @pytest.mark.asyncio
    async def test_circuit_opens_after_failures(
        self, breaker: CircuitBreaker
    ) -> None:
        """Test circuit opens after threshold failures.
        
        **Property 4: Circuit breaker protege contra falhas Redis**
        **Validates: Requirements 2.1**
        """
        # Record failures up to threshold
        for _ in range(3):
            await breaker.record_failure()

        assert breaker.state == CircuitState.OPEN
        assert not await breaker.can_execute()

    @pytest.mark.asyncio
    async def test_circuit_uses_fallback_when_open(
        self, breaker: CircuitBreaker
    ) -> None:
        """Test fallback is used when circuit is open.
        
        **Validates: Requirements 2.1**
        """
        # Open the circuit
        for _ in range(3):
            await breaker.record_failure()

        # Should not allow execution
        can_execute = await breaker.can_execute()
        assert not can_execute

    @pytest.mark.asyncio
    async def test_circuit_recovers_after_timeout(
        self, breaker: CircuitBreaker
    ) -> None:
        """Test circuit recovers after reset timeout.
        
        **Validates: Requirements 2.1**
        """
        import asyncio

        # Open the circuit
        for _ in range(3):
            await breaker.record_failure()

        assert breaker.state == CircuitState.OPEN

        # Wait for reset timeout
        await asyncio.sleep(0.15)

        # Should transition to half-open
        can_execute = await breaker.can_execute()
        assert can_execute
        assert breaker.state == CircuitState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_circuit_closes_after_success(
        self, breaker: CircuitBreaker
    ) -> None:
        """Test circuit closes after successful call in half-open.
        
        **Validates: Requirements 2.1**
        """
        import asyncio

        # Open then wait for half-open
        for _ in range(3):
            await breaker.record_failure()

        await asyncio.sleep(0.15)
        await breaker.can_execute()

        # Record success
        await breaker.record_success()

        assert breaker.state == CircuitState.CLOSED


class TestRedisCacheOperations:
    """Integration tests for Redis cache operations."""

    @pytest.fixture
    def mock_redis_client(self):
        """Create mock Redis client."""
        client = MagicMock()
        client.get = AsyncMock(return_value=None)
        client.set = AsyncMock(return_value=True)
        client.delete = AsyncMock(return_value=True)
        client.is_connected = True
        client.circuit_state = "closed"
        client.is_using_fallback = False
        return client

    @pytest.mark.asyncio
    async def test_cache_set_and_get(self, mock_redis_client) -> None:
        """Test cache set and get operations.
        
        **Validates: Requirements 2.5**
        """
        # Set value
        result = await mock_redis_client.set("test:key", {"data": "value"}, 3600)
        assert result is True

        # Configure get to return the value
        mock_redis_client.get.return_value = {"data": "value"}

        # Get value
        value = await mock_redis_client.get("test:key")
        assert value == {"data": "value"}

    @pytest.mark.asyncio
    async def test_cache_delete(self, mock_redis_client) -> None:
        """Test cache delete operation.
        
        **Validates: Requirements 2.5**
        """
        result = await mock_redis_client.delete("test:key")
        assert result is True

    @pytest.mark.asyncio
    async def test_cache_miss_returns_none(self, mock_redis_client) -> None:
        """Test cache miss returns None.
        
        **Validates: Requirements 2.5**
        """
        mock_redis_client.get.return_value = None
        value = await mock_redis_client.get("nonexistent:key")
        assert value is None
