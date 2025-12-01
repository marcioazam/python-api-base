"""Property-based tests for Sliding Window Rate Limiter.

**Feature: api-base-score-100, Task 2.3: Write property test for weighted count**
**Feature: api-base-score-100, Task 2.4: Write property test for 429 response**
**Validates: Requirements 2.2, 2.3**
"""

import asyncio
import time
from unittest.mock import patch

import pytest
from hypothesis import given, settings, strategies as st

from my_app.adapters.api.middleware.sliding_window import (
    RateLimitConfigError,
    SlidingWindowConfig,
    SlidingWindowRateLimiter,
    WindowState,
    parse_rate_limit,
)


class TestSlidingWindowWeightedCount:
    """Property tests for sliding window weighted count calculation.

    **Feature: api-base-score-100, Property 4: Sliding Window Weighted Count**
    **Validates: Requirements 2.2**
    """

    @given(
        previous_count=st.integers(min_value=0, max_value=1000),
        current_count=st.integers(min_value=0, max_value=1000),
        elapsed_fraction=st.floats(min_value=0.0, max_value=0.99),
    )
    @settings(max_examples=100)
    def test_weighted_count_formula(
        self,
        previous_count: int,
        current_count: int,
        elapsed_fraction: float,
    ) -> None:
        """Weighted count equals: previous * (1 - elapsed/window) + current.

        **Feature: api-base-score-100, Property 4: Sliding Window Weighted Count**
        **Validates: Requirements 2.2**
        """
        window_size = 60
        config = SlidingWindowConfig(
            requests_per_window=1000,
            window_size_seconds=window_size,
        )
        limiter = SlidingWindowRateLimiter(config)

        now = time.time()
        window_start = (now // window_size) * window_size
        elapsed = elapsed_fraction * window_size

        state = WindowState(
            window_start=window_start,
            current_count=current_count,
            previous_count=previous_count,
        )

        test_time = window_start + elapsed
        weight = 1.0 - (elapsed / window_size)
        expected = previous_count * weight + current_count

        actual = limiter._calculate_weighted_count(state, test_time)

        assert abs(actual - expected) < 0.001

    @given(
        requests_per_window=st.integers(min_value=1, max_value=10000),
        window_size=st.integers(min_value=1, max_value=86400),
    )
    @settings(max_examples=100)
    def test_config_validation(
        self,
        requests_per_window: int,
        window_size: int,
    ) -> None:
        """Valid config parameters create valid configuration.

        **Feature: api-base-score-100, Property 4: Sliding Window Weighted Count**
        **Validates: Requirements 2.2**
        """
        config = SlidingWindowConfig(
            requests_per_window=requests_per_window,
            window_size_seconds=window_size,
        )

        assert config.requests_per_window == requests_per_window
        assert config.window_size_seconds == window_size


class TestRateLimitFormatParsing:
    """Property tests for rate limit format parsing.

    **Feature: api-base-score-100, Property 6: Rate Limit Format Parsing**
    **Validates: Requirements 2.4**
    """

    @given(
        requests=st.integers(min_value=1, max_value=100000),
        unit=st.sampled_from(["second", "minute", "hour", "day"]),
    )
    @settings(max_examples=100)
    def test_parse_valid_rate_limit(self, requests: int, unit: str) -> None:
        """Valid rate limit strings parse correctly.

        **Feature: api-base-score-100, Property 6: Rate Limit Format Parsing**
        **Validates: Requirements 2.4**
        """
        rate_limit = f"{requests}/{unit}"
        config = parse_rate_limit(rate_limit)

        assert config.requests_per_window == requests

        expected_seconds = {
            "second": 1,
            "minute": 60,
            "hour": 3600,
            "day": 86400,
        }
        assert config.window_size_seconds == expected_seconds[unit]

    def test_invalid_format_raises_error(self) -> None:
        """Invalid format raises RateLimitConfigError."""
        with pytest.raises(RateLimitConfigError):
            parse_rate_limit("invalid")

        with pytest.raises(RateLimitConfigError):
            parse_rate_limit("100/invalid_unit")

        with pytest.raises(RateLimitConfigError):
            parse_rate_limit("")


class TestRateLimit429Response:
    """Property tests for rate limit 429 response.

    **Feature: api-base-score-100, Property 5: Rate Limit 429 Response**
    **Validates: Requirements 2.3**
    """

    @pytest.mark.asyncio
    @given(
        limit=st.integers(min_value=1, max_value=100),
    )
    @settings(max_examples=50)
    async def test_exceeding_limit_returns_not_allowed(self, limit: int) -> None:
        """Exceeding rate limit returns allowed=False.

        **Feature: api-base-score-100, Property 5: Rate Limit 429 Response**
        **Validates: Requirements 2.3**
        """
        config = SlidingWindowConfig(
            requests_per_window=limit,
            window_size_seconds=60,
        )
        limiter = SlidingWindowRateLimiter(config)

        key = f"test_key_{limit}"

        for _ in range(limit):
            result = await limiter.is_allowed(key)
            assert result.allowed is True

        result = await limiter.is_allowed(key)
        assert result.allowed is False
        assert result.retry_after > 0
        assert result.remaining == 0

    @pytest.mark.asyncio
    async def test_retry_after_is_positive(self) -> None:
        """Retry-After header is always positive when rate limited.

        **Feature: api-base-score-100, Property 5: Rate Limit 429 Response**
        **Validates: Requirements 2.3**
        """
        config = SlidingWindowConfig(
            requests_per_window=1,
            window_size_seconds=60,
        )
        limiter = SlidingWindowRateLimiter(config)

        await limiter.is_allowed("test")
        result = await limiter.is_allowed("test")

        assert result.allowed is False
        assert result.retry_after >= 1

    @pytest.mark.asyncio
    @given(
        limit=st.integers(min_value=5, max_value=50),
    )
    @settings(max_examples=50)
    async def test_remaining_decreases_with_requests(self, limit: int) -> None:
        """Remaining count decreases with each request.

        **Feature: api-base-score-100, Property 5: Rate Limit 429 Response**
        **Validates: Requirements 2.3**
        """
        config = SlidingWindowConfig(
            requests_per_window=limit,
            window_size_seconds=60,
        )
        limiter = SlidingWindowRateLimiter(config)

        key = f"remaining_test_{limit}"
        previous_remaining = limit

        for i in range(min(limit, 10)):
            result = await limiter.is_allowed(key)
            if result.allowed:
                assert result.remaining <= previous_remaining
                previous_remaining = result.remaining


class TestSlidingWindowInvalidConfig:
    """Tests for invalid configuration handling."""

    def test_zero_requests_raises_error(self) -> None:
        """Zero requests per window raises error."""
        with pytest.raises(RateLimitConfigError):
            SlidingWindowConfig(requests_per_window=0, window_size_seconds=60)

    def test_negative_requests_raises_error(self) -> None:
        """Negative requests per window raises error."""
        with pytest.raises(RateLimitConfigError):
            SlidingWindowConfig(requests_per_window=-1, window_size_seconds=60)

    def test_zero_window_size_raises_error(self) -> None:
        """Zero window size raises error."""
        with pytest.raises(RateLimitConfigError):
            SlidingWindowConfig(requests_per_window=100, window_size_seconds=0)

    def test_negative_window_size_raises_error(self) -> None:
        """Negative window size raises error."""
        with pytest.raises(RateLimitConfigError):
            SlidingWindowConfig(requests_per_window=100, window_size_seconds=-1)
