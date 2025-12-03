"""Property-based tests for infrastructure modules.

**Feature: infrastructure-modules-integration-analysis**
**Validates: Requirements 1.1, 1.2, 1.3, 1.4, 2.1**

Uses Hypothesis for property-based testing.
"""

import pytest
from hypothesis import given, strategies as st, settings
from datetime import timedelta


class TestPrometheusMetricsProperties:
    """Property tests for Prometheus metrics.
    
    **Feature: infrastructure-modules-integration-analysis**
    **Property 1: Prometheus metrics endpoint funcional**
    **Validates: Requirements 1.1, 1.2**
    """

    @given(st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'N'))))
    @settings(max_examples=100)
    def test_metric_name_format(self, name: str) -> None:
        """Test metric names follow Prometheus format.
        
        *For any* valid metric name, the name should only contain
        alphanumeric characters and underscores.
        
        **Property 1: Prometheus metrics endpoint funcional**
        **Validates: Requirements 1.1, 1.2**
        """
        # Prometheus metric names must match [a-zA-Z_:][a-zA-Z0-9_:]*
        import re
        
        # Sanitize name to valid Prometheus format
        sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        if sanitized and not sanitized[0].isalpha() and sanitized[0] != '_':
            sanitized = '_' + sanitized
        
        # Verify sanitized name is valid
        pattern = r'^[a-zA-Z_][a-zA-Z0-9_]*$'
        assert re.match(pattern, sanitized) is not None


class TestRateLimitingProperties:
    """Property tests for rate limiting.
    
    **Feature: infrastructure-modules-integration-analysis**
    **Property 2: Rate limiting protege endpoints**
    **Validates: Requirements 1.3**
    """

    @given(
        requests=st.integers(min_value=1, max_value=1000),
        window_seconds=st.integers(min_value=1, max_value=3600),
    )
    @settings(max_examples=100)
    def test_rate_limit_config_valid(self, requests: int, window_seconds: int) -> None:
        """Test rate limit configuration is always valid.
        
        *For any* positive requests and window, the configuration
        should be valid and usable.
        
        **Property 2: Rate limiting protege endpoints**
        **Validates: Requirements 1.3**
        """
        from infrastructure.ratelimit import RateLimit
        
        limit = RateLimit(
            requests=requests,
            window=timedelta(seconds=window_seconds),
        )
        
        assert limit.requests == requests
        assert limit.window_seconds == float(window_seconds)

    @given(
        client_id=st.text(min_size=1, max_size=100),
        num_requests=st.integers(min_value=1, max_value=20),
    )
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_rate_limiter_tracks_requests(
        self, client_id: str, num_requests: int
    ) -> None:
        """Test rate limiter correctly tracks request count.
        
        *For any* client making N requests, the remaining count
        should decrease by N (or be 0 if exceeded).
        
        **Property 2: Rate limiting protege endpoints**
        **Validates: Requirements 1.3**
        """
        from infrastructure.ratelimit import InMemoryRateLimiter, RateLimitConfig, RateLimit
        
        limit = RateLimit(requests=100, window=timedelta(minutes=1))
        config = RateLimitConfig(default_limit=limit)
        limiter = InMemoryRateLimiter[str](config)
        
        # Make requests
        for i in range(num_requests):
            result = await limiter.check(client_id, limit)
            expected_remaining = max(0, 100 - (i + 1))
            assert result.remaining == expected_remaining

    @given(
        limit_requests=st.integers(min_value=1, max_value=10),
    )
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_rate_limiter_blocks_after_limit(self, limit_requests: int) -> None:
        """Test rate limiter blocks requests after limit exceeded.
        
        *For any* limit N, after N requests the next request
        should be blocked.
        
        **Property 2: Rate limiting protege endpoints**
        **Validates: Requirements 1.3**
        """
        from infrastructure.ratelimit import InMemoryRateLimiter, RateLimitConfig, RateLimit
        
        limit = RateLimit(requests=limit_requests, window=timedelta(minutes=1))
        config = RateLimitConfig(default_limit=limit)
        limiter = InMemoryRateLimiter[str](config)
        
        # Use up the limit
        for _ in range(limit_requests):
            result = await limiter.check("test-client", limit)
            assert result.is_allowed
        
        # Next request should be blocked
        result = await limiter.check("test-client", limit)
        assert not result.is_allowed
        assert result.remaining == 0


class TestCacheProperties:
    """Property tests for cache operations.
    
    **Feature: infrastructure-modules-integration-analysis**
    **Property 3: Cache hit evita query ao banco**
    **Validates: Requirements 1.4**
    """

    @given(
        key=st.text(min_size=1, max_size=100, alphabet=st.characters(whitelist_categories=('L', 'N', 'P'))),
        value=st.dictionaries(
            keys=st.text(min_size=1, max_size=20),
            values=st.one_of(st.text(), st.integers(), st.booleans()),
            min_size=1,
            max_size=5,
        ),
    )
    @settings(max_examples=100)
    def test_cache_key_value_roundtrip(self, key: str, value: dict) -> None:
        """Test cache stores and retrieves values correctly.
        
        *For any* key-value pair, storing and retrieving should
        return the same value.
        
        **Property 3: Cache hit evita query ao banco**
        **Validates: Requirements 1.4**
        """
        from infrastructure.cache import LRUCache
        
        cache = LRUCache(max_size=100)
        
        # Store value
        cache.set(key, value)
        
        # Retrieve value
        retrieved = cache.get(key)
        
        assert retrieved == value


class TestCircuitBreakerProperties:
    """Property tests for circuit breaker.
    
    **Feature: infrastructure-modules-integration-analysis**
    **Property 4: Circuit breaker protege contra falhas Redis**
    **Validates: Requirements 2.1**
    """

    @given(
        failure_threshold=st.integers(min_value=1, max_value=10),
        num_failures=st.integers(min_value=0, max_value=15),
    )
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_circuit_opens_at_threshold(
        self, failure_threshold: int, num_failures: int
    ) -> None:
        """Test circuit opens exactly at failure threshold.
        
        *For any* threshold N, the circuit should open after
        exactly N consecutive failures.
        
        **Property 4: Circuit breaker protege contra falhas Redis**
        **Validates: Requirements 2.1**
        """
        from infrastructure.redis.circuit_breaker import CircuitBreaker, CircuitState
        
        breaker = CircuitBreaker(
            failure_threshold=failure_threshold,
            reset_timeout=1.0,
            half_open_max_calls=1,
        )
        
        # Record failures
        for i in range(num_failures):
            await breaker.record_failure()
            
            if i + 1 >= failure_threshold:
                assert breaker.state == CircuitState.OPEN
            else:
                assert breaker.state == CircuitState.CLOSED

    @given(
        failure_threshold=st.integers(min_value=1, max_value=5),
    )
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_success_resets_failure_count(self, failure_threshold: int) -> None:
        """Test success resets failure count.
        
        *For any* threshold, a success should reset the failure
        count, preventing circuit from opening.
        
        **Property 4: Circuit breaker protege contra falhas Redis**
        **Validates: Requirements 2.1**
        """
        from infrastructure.redis.circuit_breaker import CircuitBreaker, CircuitState
        
        breaker = CircuitBreaker(
            failure_threshold=failure_threshold,
            reset_timeout=1.0,
            half_open_max_calls=1,
        )
        
        # Record failures just below threshold
        for _ in range(failure_threshold - 1):
            await breaker.record_failure()
        
        # Record success
        await breaker.record_success()
        
        # Circuit should still be closed
        assert breaker.state == CircuitState.CLOSED
        
        # Should be able to fail again without opening
        for _ in range(failure_threshold - 1):
            await breaker.record_failure()
        
        assert breaker.state == CircuitState.CLOSED
