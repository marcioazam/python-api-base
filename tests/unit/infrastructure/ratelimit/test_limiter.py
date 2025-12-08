"""Tests for rate limiter module.

Tests for RateLimitResult, InMemoryRateLimiter, and SlidingWindowLimiter.
"""

from datetime import UTC, datetime, timedelta

import pytest

from infrastructure.ratelimit.config import RateLimit, RateLimitConfig
from infrastructure.ratelimit.limiter import (
    InMemoryRateLimiter,
    RateLimitResult,
    SlidingWindowLimiter,
)


class TestRateLimitResult:
    """Tests for RateLimitResult dataclass."""

    def test_init_allowed(self) -> None:
        """RateLimitResult should store allowed state."""
        result: RateLimitResult[str] = RateLimitResult(
            client="user1",
            is_allowed=True,
            remaining=9,
            limit=10,
            reset_at=datetime.now(UTC),
        )
        assert result.is_allowed is True
        assert result.remaining == 9

    def test_init_denied(self) -> None:
        """RateLimitResult should store denied state."""
        result: RateLimitResult[str] = RateLimitResult(
            client="user1",
            is_allowed=False,
            remaining=0,
            limit=10,
            reset_at=datetime.now(UTC),
            retry_after=timedelta(seconds=30),
        )
        assert result.is_allowed is False
        assert result.retry_after == timedelta(seconds=30)

    def test_headers_basic(self) -> None:
        """headers should return rate limit headers."""
        reset_time = datetime.now(UTC)
        result: RateLimitResult[str] = RateLimitResult(
            client="user1",
            is_allowed=True,
            remaining=5,
            limit=10,
            reset_at=reset_time,
        )
        headers = result.headers
        assert headers["X-RateLimit-Limit"] == "10"
        assert headers["X-RateLimit-Remaining"] == "5"
        assert "X-RateLimit-Reset" in headers

    def test_headers_with_retry_after(self) -> None:
        """headers should include Retry-After when rate limited."""
        result: RateLimitResult[str] = RateLimitResult(
            client="user1",
            is_allowed=False,
            remaining=0,
            limit=10,
            reset_at=datetime.now(UTC),
            retry_after=timedelta(seconds=60),
        )
        headers = result.headers
        assert headers["Retry-After"] == "60"

    def test_headers_remaining_not_negative(self) -> None:
        """headers should not show negative remaining."""
        result: RateLimitResult[str] = RateLimitResult(
            client="user1",
            is_allowed=False,
            remaining=-5,
            limit=10,
            reset_at=datetime.now(UTC),
        )
        headers = result.headers
        assert headers["X-RateLimit-Remaining"] == "0"

    def test_is_frozen(self) -> None:
        """RateLimitResult should be immutable."""
        result: RateLimitResult[str] = RateLimitResult(
            client="user1",
            is_allowed=True,
            remaining=5,
            limit=10,
            reset_at=datetime.now(UTC),
        )
        with pytest.raises(AttributeError):
            result.remaining = 0  # type: ignore


class TestInMemoryRateLimiter:
    """Tests for InMemoryRateLimiter class."""

    @pytest.fixture
    def config(self) -> RateLimitConfig:
        """Create test config."""
        return RateLimitConfig()

    @pytest.fixture
    def limiter(self, config: RateLimitConfig) -> InMemoryRateLimiter[str]:
        """Create test limiter."""
        return InMemoryRateLimiter(config)

    @pytest.mark.asyncio
    async def test_first_request_allowed(
        self, limiter: InMemoryRateLimiter[str]
    ) -> None:
        """First request should be allowed."""
        limit = RateLimit(requests=10, window=timedelta(minutes=1))
        result = await limiter.check("user1", limit)
        assert result.is_allowed is True
        assert result.remaining == 9

    @pytest.mark.asyncio
    async def test_multiple_requests_allowed(
        self, limiter: InMemoryRateLimiter[str]
    ) -> None:
        """Multiple requests within limit should be allowed."""
        limit = RateLimit(requests=5, window=timedelta(minutes=1))
        for i in range(5):
            result = await limiter.check("user1", limit)
            assert result.is_allowed is True
            assert result.remaining == 4 - i

    @pytest.mark.asyncio
    async def test_exceeds_limit(self, limiter: InMemoryRateLimiter[str]) -> None:
        """Requests exceeding limit should be denied."""
        limit = RateLimit(requests=3, window=timedelta(minutes=1))
        for _ in range(3):
            await limiter.check("user1", limit)

        result = await limiter.check("user1", limit)
        assert result.is_allowed is False
        assert result.remaining == 0
        assert result.retry_after is not None

    @pytest.mark.asyncio
    async def test_different_clients_independent(
        self, limiter: InMemoryRateLimiter[str]
    ) -> None:
        """Different clients should have independent limits."""
        limit = RateLimit(requests=2, window=timedelta(minutes=1))

        # Exhaust user1's limit
        await limiter.check("user1", limit)
        await limiter.check("user1", limit)
        result1 = await limiter.check("user1", limit)
        assert result1.is_allowed is False

        # user2 should still be allowed
        result2 = await limiter.check("user2", limit)
        assert result2.is_allowed is True

    @pytest.mark.asyncio
    async def test_different_endpoints_independent(
        self, limiter: InMemoryRateLimiter[str]
    ) -> None:
        """Different endpoints should have independent limits."""
        limit = RateLimit(requests=1, window=timedelta(minutes=1))

        result1 = await limiter.check("user1", limit, endpoint="api/users")
        assert result1.is_allowed is True

        result2 = await limiter.check("user1", limit, endpoint="api/posts")
        assert result2.is_allowed is True

    @pytest.mark.asyncio
    async def test_reset_clears_limit(
        self, limiter: InMemoryRateLimiter[str]
    ) -> None:
        """reset should clear rate limit for client."""
        limit = RateLimit(requests=1, window=timedelta(minutes=1))

        await limiter.check("user1", limit)
        result1 = await limiter.check("user1", limit)
        assert result1.is_allowed is False

        reset_result = await limiter.reset("user1")
        assert reset_result is True

        result2 = await limiter.check("user1", limit)
        assert result2.is_allowed is True

    @pytest.mark.asyncio
    async def test_reset_nonexistent_returns_false(
        self, limiter: InMemoryRateLimiter[str]
    ) -> None:
        """reset should return False for nonexistent client."""
        result = await limiter.reset("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_result_contains_client(
        self, limiter: InMemoryRateLimiter[str]
    ) -> None:
        """Result should contain client identifier."""
        limit = RateLimit(requests=10, window=timedelta(minutes=1))
        result = await limiter.check("my-client", limit)
        assert result.client == "my-client"

    @pytest.mark.asyncio
    async def test_result_contains_limit(
        self, limiter: InMemoryRateLimiter[str]
    ) -> None:
        """Result should contain limit value."""
        limit = RateLimit(requests=100, window=timedelta(minutes=1))
        result = await limiter.check("user1", limit)
        assert result.limit == 100


class TestSlidingWindowLimiter:
    """Tests for SlidingWindowLimiter class."""

    @pytest.fixture
    def config(self) -> RateLimitConfig:
        """Create test config."""
        return RateLimitConfig()

    @pytest.fixture
    def limiter(self, config: RateLimitConfig) -> SlidingWindowLimiter[str]:
        """Create test limiter without Redis (uses fallback)."""
        return SlidingWindowLimiter(config, redis_client=None)

    @pytest.mark.asyncio
    async def test_fallback_to_memory(
        self, limiter: SlidingWindowLimiter[str]
    ) -> None:
        """Should fallback to in-memory when no Redis."""
        limit = RateLimit(requests=10, window=timedelta(minutes=1))
        result = await limiter.check("user1", limit)
        assert result.is_allowed is True

    @pytest.mark.asyncio
    async def test_fallback_reset(self, limiter: SlidingWindowLimiter[str]) -> None:
        """reset should work with fallback."""
        limit = RateLimit(requests=1, window=timedelta(minutes=1))
        await limiter.check("user1", limit)

        result = await limiter.reset("user1")
        assert result is True

    @pytest.mark.asyncio
    async def test_configure_limits(self, config: RateLimitConfig) -> None:
        """configure should set per-endpoint limits."""
        limiter: SlidingWindowLimiter[str] = SlidingWindowLimiter(config)
        custom_limit = RateLimit(requests=50, window=timedelta(minutes=5))
        limiter.configure({"api/special": custom_limit})

        retrieved = limiter.get_limit("api/special")
        assert retrieved.requests == 50

    @pytest.mark.asyncio
    async def test_get_limit_default(self, config: RateLimitConfig) -> None:
        """get_limit should return default for unconfigured endpoint."""
        limiter: SlidingWindowLimiter[str] = SlidingWindowLimiter(config)
        limit = limiter.get_limit("unknown/endpoint")
        assert limit == config.default_limit
