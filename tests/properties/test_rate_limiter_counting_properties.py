"""Property-based tests for Rate Limiter Request Counting.

**Feature: architecture-restructuring-2025, Property 14: Rate Limiter Request Counting**
**Validates: Requirements 9.4**
"""

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

try:
    from infrastructure.security.sliding_window import (
        SlidingWindowConfig,
        SlidingWindowRateLimiter,
        RateLimitResult,
        parse_rate_limit,
    )
except ImportError:
    pytest.skip("my_app modules not available", allow_module_level=True)


# Strategy for rate limit values
requests_strategy = st.integers(min_value=1, max_value=100)
window_strategy = st.integers(min_value=1, max_value=3600)
key_strategy = st.text(min_size=1, max_size=50, alphabet="abcdefghijklmnopqrstuvwxyz0123456789:_-")


class TestRateLimiterCounting:
    """Property tests for rate limiter request counting."""

    @settings(max_examples=50)
    @given(max_requests=requests_strategy, key=key_strategy)
    @pytest.mark.asyncio
    async def test_n_requests_succeed_then_rejected(
        self, max_requests: int, key: str
    ) -> None:
        """
        **Feature: architecture-restructuring-2025, Property 14: Rate Limiter Request Counting**
        
        For any rate limit of N requests per window, making N requests SHALL succeed,
        and the (N+1)th request SHALL be rejected.
        **Validates: Requirements 9.4**
        """
        config = SlidingWindowConfig(
            requests_per_window=max_requests,
            window_size_seconds=60,
        )
        limiter = SlidingWindowRateLimiter(config)
        
        # Make N requests - all should succeed
        for i in range(max_requests):
            result = await limiter.is_allowed(key)
            assert result.allowed is True, f"Request {i+1} of {max_requests} should be allowed"
        
        # (N+1)th request should be rejected
        result = await limiter.is_allowed(key)
        assert result.allowed is False
        assert result.remaining == 0
        assert result.retry_after > 0

    @settings(max_examples=30)
    @given(max_requests=requests_strategy, key=key_strategy)
    @pytest.mark.asyncio
    async def test_remaining_decreases_with_requests(
        self, max_requests: int, key: str
    ) -> None:
        """
        For each request, the remaining count SHALL decrease.
        **Validates: Requirements 9.4**
        """
        assume(max_requests >= 3)
        
        config = SlidingWindowConfig(
            requests_per_window=max_requests,
            window_size_seconds=60,
        )
        limiter = SlidingWindowRateLimiter(config)
        
        previous_remaining = max_requests
        for _ in range(min(max_requests, 5)):
            result = await limiter.is_allowed(key)
            if result.allowed:
                assert result.remaining < previous_remaining or result.remaining == 0
                previous_remaining = result.remaining

    @settings(max_examples=30)
    @given(key1=key_strategy, key2=key_strategy, max_requests=requests_strategy)
    @pytest.mark.asyncio
    async def test_different_keys_independent(
        self, key1: str, key2: str, max_requests: int
    ) -> None:
        """
        For different keys, rate limits SHALL be tracked independently.
        **Validates: Requirements 9.4**
        """
        assume(key1 != key2)
        
        config = SlidingWindowConfig(
            requests_per_window=max_requests,
            window_size_seconds=60,
        )
        limiter = SlidingWindowRateLimiter(config)
        
        # Exhaust key1's limit
        for _ in range(max_requests):
            await limiter.is_allowed(key1)
        
        # key1 should be blocked
        result1 = await limiter.is_allowed(key1)
        assert result1.allowed is False
        
        # key2 should still be allowed
        result2 = await limiter.is_allowed(key2)
        assert result2.allowed is True

    @settings(max_examples=20)
    @given(key=key_strategy)
    @pytest.mark.asyncio
    async def test_reset_clears_limit(self, key: str) -> None:
        """
        After reset, the rate limit SHALL be cleared for that key.
        **Validates: Requirements 9.4**
        """
        config = SlidingWindowConfig(
            requests_per_window=5,
            window_size_seconds=60,
        )
        limiter = SlidingWindowRateLimiter(config)
        
        # Exhaust limit
        for _ in range(5):
            await limiter.is_allowed(key)
        
        # Should be blocked
        result = await limiter.is_allowed(key)
        assert result.allowed is False
        
        # Reset
        await limiter.reset(key)
        
        # Should be allowed again
        result = await limiter.is_allowed(key)
        assert result.allowed is True

    @settings(max_examples=20)
    @given(
        requests=st.integers(min_value=1, max_value=1000),
        unit=st.sampled_from(["second", "minute", "hour", "day"]),
    )
    def test_parse_rate_limit_format(self, requests: int, unit: str) -> None:
        """
        For any valid rate limit string, parsing SHALL produce correct config.
        **Validates: Requirements 9.4**
        """
        rate_string = f"{requests}/{unit}"
        config = parse_rate_limit(rate_string)
        
        assert config.requests_per_window == requests
        
        expected_seconds = {
            "second": 1,
            "minute": 60,
            "hour": 3600,
            "day": 86400,
        }
        assert config.window_size_seconds == expected_seconds[unit]

    @settings(max_examples=30)
    @given(max_requests=requests_strategy, key=key_strategy)
    @pytest.mark.asyncio
    async def test_rejected_request_has_retry_info(
        self, max_requests: int, key: str
    ) -> None:
        """
        For any rejected request, retry_after SHALL be positive.
        **Validates: Requirements 9.4**
        """
        config = SlidingWindowConfig(
            requests_per_window=max_requests,
            window_size_seconds=60,
        )
        limiter = SlidingWindowRateLimiter(config)
        
        # Exhaust limit
        for _ in range(max_requests):
            await limiter.is_allowed(key)
        
        # Rejected request should have retry info
        result = await limiter.is_allowed(key)
        assert result.allowed is False
        assert result.retry_after > 0
        assert result.retry_after <= 60  # Should be within window
