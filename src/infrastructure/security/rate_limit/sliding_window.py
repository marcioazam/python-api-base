"""Sliding Window Rate Limiter implementation.

**Feature: api-base-score-100, Task 2.1: Create SlidingWindowRateLimiter class**
**Feature: api-base-score-100, Task 5.2: Add comprehensive docstrings to rate limiter**
**Validates: Requirements 2.1, 2.2, 4.1, 4.3**

This module implements a sliding window rate limiting algorithm that provides
smoother traffic distribution compared to fixed window approaches.

Algorithm Overview:
    The sliding window algorithm calculates a weighted request count based on
    both the current and previous time windows. This prevents the "burst at
    window boundary" problem common with fixed window rate limiters.

    Formula: weighted_count = previous_count * (1 - elapsed/window_size) + current_count

    Where:
        - previous_count: Requests in the previous window
        - current_count: Requests in the current window
        - elapsed: Time elapsed in current window
        - window_size: Total window duration

Benefits over Fixed Window:
    - Smoother traffic distribution
    - No burst allowance at window boundaries
    - More accurate rate limiting
    - Better protection against traffic spikes

Configuration:
    Rate limits are specified in format "N/unit" where:
        - N: Maximum requests allowed
        - unit: Time unit (second, minute, hour, day)

    Examples:
        - "100/minute": 100 requests per minute
        - "1000/hour": 1000 requests per hour
        - "10/second": 10 requests per second

Example Usage:
    >>> from interface.middleware.sliding_window import (
    ...     SlidingWindowConfig,
    ...     SlidingWindowRateLimiter,
    ...     parse_rate_limit,
    ... )
    >>> config = parse_rate_limit("100/minute")
    >>> limiter = SlidingWindowRateLimiter(config)
    >>> result = await limiter.is_allowed("user:123")
    >>> if not result.allowed:
    ...     print(f"Rate limited. Retry after {result.retry_after}s")
"""

import asyncio
import logging
import re
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class RateLimitConfigError(Exception):
    """Raised when rate limit configuration is invalid."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


@dataclass(frozen=True, slots=True)
class SlidingWindowConfig:
    """Sliding window rate limiter configuration.

    **Feature: api-base-score-100, Property 6: Rate Limit Format Parsing**
    **Validates: Requirements 2.4**

    Attributes:
        requests_per_window: Maximum requests allowed per window.
        window_size_seconds: Window size in seconds.
    """

    requests_per_window: int
    window_size_seconds: int

    def __post_init__(self) -> None:
        """Validate configuration."""
        if self.requests_per_window <= 0:
            raise RateLimitConfigError("requests_per_window must be positive")
        if self.window_size_seconds <= 0:
            raise RateLimitConfigError("window_size_seconds must be positive")

    @classmethod
    def from_string(cls, rate_limit: str) -> "SlidingWindowConfig":
        """Parse rate limit string like '100/minute'.

        **Feature: api-base-score-100, Property 6: Rate Limit Format Parsing**
        **Validates: Requirements 2.4**

        Args:
            rate_limit: Rate limit string (e.g., '100/minute', '1000/hour').

        Returns:
            SlidingWindowConfig instance.

        Raises:
            RateLimitConfigError: If format is invalid.
        """
        pattern = r"^(\d+)/(\w+)$"
        match = re.match(pattern, rate_limit.strip())

        if not match:
            raise RateLimitConfigError(
                f"Invalid rate limit format: '{rate_limit}'. "
                "Expected format: 'N/unit' (e.g., '100/minute')"
            )

        requests = int(match.group(1))
        unit = match.group(2).lower()

        unit_seconds = {
            "second": 1,
            "seconds": 1,
            "minute": 60,
            "minutes": 60,
            "hour": 3600,
            "hours": 3600,
            "day": 86400,
            "days": 86400,
        }

        if unit not in unit_seconds:
            raise RateLimitConfigError(
                f"Invalid time unit: '{unit}'. "
                f"Valid units: {', '.join(unit_seconds.keys())}"
            )

        return cls(
            requests_per_window=requests,
            window_size_seconds=unit_seconds[unit],
        )


@dataclass
class WindowState:
    """State of a rate limit window.

    Attributes:
        window_start: Start timestamp of current window.
        current_count: Request count in current window.
        previous_count: Request count in previous window.
    """

    window_start: float
    current_count: int = 0
    previous_count: int = 0


@dataclass
class RateLimitResult:
    """Result of rate limit check.

    Attributes:
        allowed: Whether request is allowed.
        remaining: Remaining requests in window.
        retry_after: Seconds until rate limit resets (if blocked).
        weighted_count: Current weighted request count.
    """

    allowed: bool
    remaining: int
    retry_after: int
    weighted_count: float


class SlidingWindowRateLimiter:
    """Rate limiter using sliding window algorithm.

    **Feature: api-base-score-100, Task 2.1: Create SlidingWindowRateLimiter class**
    **Validates: Requirements 2.1, 2.2**

    The sliding window algorithm provides smoother rate limiting by
    considering requests from both current and previous windows with
    weighted counts based on elapsed time.

    Formula: weighted_count = previous_count * (1 - elapsed/window_size) + current_count

    Example:
        >>> config = SlidingWindowConfig(requests_per_window=100, window_size_seconds=60)
        >>> limiter = SlidingWindowRateLimiter(config)
        >>> result = await limiter.is_allowed("user:123")
        >>> if not result.allowed:
        ...     print(f"Rate limited. Retry after {result.retry_after}s")
    """

    def __init__(self, config: SlidingWindowConfig) -> None:
        """Initialize sliding window rate limiter.

        Args:
            config: Rate limiter configuration.
        """
        self._config = config
        self._windows: dict[str, WindowState] = {}
        self._lock = asyncio.Lock()

    def _get_current_window_start(self, now: float) -> float:
        """Get start timestamp of current window."""
        return (
            now // self._config.window_size_seconds
        ) * self._config.window_size_seconds

    def _calculate_weighted_count(
        self,
        state: WindowState,
        now: float,
    ) -> float:
        """Calculate weighted request count using sliding window.

        **Feature: api-base-score-100, Property 4: Sliding Window Weighted Count**
        **Validates: Requirements 2.2**

        Formula: previous_count * (1 - elapsed/window_size) + current_count

        Args:
            state: Current window state.
            now: Current timestamp.

        Returns:
            Weighted request count.
        """
        elapsed = now - state.window_start
        window_size = self._config.window_size_seconds

        if elapsed >= window_size:
            return float(state.current_count)

        weight = 1.0 - (elapsed / window_size)
        return state.previous_count * weight + state.current_count

    def _calculate_retry_after(self, state: WindowState, now: float) -> int:
        """Calculate seconds until rate limit resets.

        Args:
            state: Current window state.
            now: Current timestamp.

        Returns:
            Seconds until retry is allowed.
        """
        window_end = state.window_start + self._config.window_size_seconds
        return max(1, int(window_end - now))

    async def is_allowed(self, key: str) -> RateLimitResult:
        """Check if request is allowed under rate limit.

        **Feature: api-base-score-100, Property 5: Rate Limit 429 Response**
        **Validates: Requirements 2.3**

        Args:
            key: Unique identifier for rate limiting (e.g., IP, user ID).

        Returns:
            RateLimitResult with allowed status and metadata.
        """
        now = time.time()
        current_window_start = self._get_current_window_start(now)

        async with self._lock:
            state = self._windows.get(key)

            if state is None:
                state = WindowState(window_start=current_window_start)
                self._windows[key] = state

            if state.window_start < current_window_start:
                if (
                    current_window_start - state.window_start
                    >= self._config.window_size_seconds
                ):
                    state = WindowState(
                        window_start=current_window_start,
                        previous_count=state.current_count,
                    )
                else:
                    state = WindowState(
                        window_start=current_window_start,
                        previous_count=state.current_count,
                    )
                self._windows[key] = state

            weighted_count = self._calculate_weighted_count(state, now)

            if weighted_count >= self._config.requests_per_window:
                retry_after = self._calculate_retry_after(state, now)
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    retry_after=retry_after,
                    weighted_count=weighted_count,
                )

            state.current_count += 1
            remaining = max(
                0, self._config.requests_per_window - int(weighted_count) - 1
            )

            return RateLimitResult(
                allowed=True,
                remaining=remaining,
                retry_after=0,
                weighted_count=weighted_count + 1,
            )

    async def get_state(self, key: str) -> WindowState | None:
        """Get current window state for a key.

        Args:
            key: Rate limit key.

        Returns:
            WindowState or None if not found.
        """
        async with self._lock:
            return self._windows.get(key)

    async def reset(self, key: str) -> bool:
        """Reset rate limit for a key.

        Args:
            key: Rate limit key.

        Returns:
            True if key existed and was reset.
        """
        async with self._lock:
            if key in self._windows:
                del self._windows[key]
                return True
            return False

    async def clear_all(self) -> int:
        """Clear all rate limit states.

        Returns:
            Number of keys cleared.
        """
        async with self._lock:
            count = len(self._windows)
            self._windows.clear()
            return count


def parse_rate_limit(rate_limit: str) -> SlidingWindowConfig:
    """Parse rate limit string to configuration.

    **Feature: api-base-score-100, Property 6: Rate Limit Format Parsing**
    **Validates: Requirements 2.4**

    Args:
        rate_limit: Rate limit string (e.g., '100/minute').

    Returns:
        SlidingWindowConfig instance.
    """
    return SlidingWindowConfig.from_string(rate_limit)
