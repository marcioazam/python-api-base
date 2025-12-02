"""Unit tests for generic rate limiter.

**Feature: enterprise-generics-2025**
**Requirement: R5 - Generic Rate Limiter**
"""

import pytest
from datetime import timedelta

from infrastructure.ratelimit.config import RateLimit, RateLimitConfig
from infrastructure.ratelimit.limiter import (
    InMemoryRateLimiter,
    RateLimitResult,
)


class TestRateLimit:
    """Tests for RateLimit configuration."""

    def test_valid_rate_limit(self) -> None:
        """Test valid rate limit creation."""
        limit = RateLimit(requests=100, window=timedelta(minutes=1))

        assert limit.requests == 100
        assert limit.window_seconds == 60.0

    def test_rate_limit_with_burst(self) -> None:
        """Test rate limit with burst allowance."""
        limit = RateLimit(requests=100, window=timedelta(minutes=1), burst=10)

        assert limit.burst == 10

    def test_invalid_requests(self) -> None:
        """Test validation rejects zero/negative requests."""
        with pytest.raises(ValueError, match="requests must be positive"):
            RateLimit(requests=0, window=timedelta(minutes=1))

    def test_invalid_window(self) -> None:
        """Test validation rejects zero/negative window."""
        with pytest.raises(ValueError, match="window must be positive"):
            RateLimit(requests=100, window=timedelta(seconds=0))


class TestRateLimitResult:
    """Tests for RateLimitResult."""

    def test_allowed_result(self) -> None:
        """Test allowed result properties."""
        from datetime import datetime, UTC

        result = RateLimitResult[str](
            client="user_123",
            is_allowed=True,
            remaining=99,
            limit=100,
            reset_at=datetime.now(UTC),
        )

        assert result.is_allowed
        assert result.remaining == 99
        assert result.retry_after is None

    def test_denied_result(self) -> None:
        """Test denied result with retry_after."""
        from datetime import datetime, UTC

        result = RateLimitResult[str](
            client="user_123",
            is_allowed=False,
            remaining=0,
            limit=100,
            reset_at=datetime.now(UTC),
            retry_after=timedelta(seconds=30),
        )

        assert not result.is_allowed
        assert result.retry_after == timedelta(seconds=30)

    def test_headers(self) -> None:
        """Test rate limit headers generation."""
        from datetime import datetime, UTC

        result = RateLimitResult[str](
            client="user_123",
            is_allowed=True,
            remaining=99,
            limit=100,
            reset_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
        )

        headers = result.headers

        assert headers["X-RateLimit-Limit"] == "100"
        assert headers["X-RateLimit-Remaining"] == "99"
        assert "X-RateLimit-Reset" in headers


class TestInMemoryRateLimiter:
    """Tests for InMemoryRateLimiter."""

    @pytest.fixture
    def config(self) -> RateLimitConfig:
        """Create test configuration."""
        return RateLimitConfig(
            default_limit=RateLimit(requests=5, window=timedelta(seconds=1))
        )

    @pytest.fixture
    def limiter(self, config: RateLimitConfig) -> InMemoryRateLimiter[str]:
        """Create test limiter."""
        return InMemoryRateLimiter[str](config)

    @pytest.mark.asyncio
    async def test_allow_under_limit(
        self,
        limiter: InMemoryRateLimiter[str],
    ) -> None:
        """Test requests under limit are allowed."""
        limit = RateLimit(requests=5, window=timedelta(seconds=60))

        result = await limiter.check("user_1", limit)

        assert result.is_allowed
        assert result.remaining == 4

    @pytest.mark.asyncio
    async def test_deny_over_limit(
        self,
        limiter: InMemoryRateLimiter[str],
    ) -> None:
        """Test requests over limit are denied."""
        limit = RateLimit(requests=3, window=timedelta(seconds=60))

        # Use up the limit
        for _ in range(3):
            await limiter.check("user_1", limit)

        # Next request should be denied
        result = await limiter.check("user_1", limit)

        assert not result.is_allowed
        assert result.remaining == 0
        assert result.retry_after is not None

    @pytest.mark.asyncio
    async def test_different_clients_independent(
        self,
        limiter: InMemoryRateLimiter[str],
    ) -> None:
        """Test different clients have independent limits."""
        limit = RateLimit(requests=2, window=timedelta(seconds=60))

        # Use up user_1's limit
        await limiter.check("user_1", limit)
        await limiter.check("user_1", limit)

        # user_2 should still be allowed
        result = await limiter.check("user_2", limit)

        assert result.is_allowed

    @pytest.mark.asyncio
    async def test_reset_client(
        self,
        limiter: InMemoryRateLimiter[str],
    ) -> None:
        """Test resetting client limit."""
        limit = RateLimit(requests=1, window=timedelta(seconds=60))

        await limiter.check("user_1", limit)
        result1 = await limiter.check("user_1", limit)
        assert not result1.is_allowed

        # Reset
        await limiter.reset("user_1")

        # Should be allowed again
        result2 = await limiter.check("user_1", limit)
        assert result2.is_allowed

    @pytest.mark.asyncio
    async def test_per_endpoint_limits(
        self,
        limiter: InMemoryRateLimiter[str],
    ) -> None:
        """Test per-endpoint limit tracking."""
        limit = RateLimit(requests=1, window=timedelta(seconds=60))

        # Different endpoints have independent limits
        result1 = await limiter.check("user_1", limit, "endpoint_a")
        result2 = await limiter.check("user_1", limit, "endpoint_b")

        assert result1.is_allowed
        assert result2.is_allowed

    @pytest.mark.asyncio
    async def test_configure_limits(
        self,
        limiter: InMemoryRateLimiter[str],
    ) -> None:
        """Test configuring per-endpoint limits."""
        limiter.configure({
            "auth": RateLimit(requests=10, window=timedelta(minutes=1)),
            "upload": RateLimit(requests=5, window=timedelta(minutes=1)),
        })

        assert limiter.get_limit("auth").requests == 10
        assert limiter.get_limit("upload").requests == 5
        # Unknown endpoint returns default
        assert limiter.get_limit("unknown").requests == 5


class TestGenericTypeParameter:
    """Tests for generic type parameter behavior."""

    @pytest.mark.asyncio
    async def test_string_client(self) -> None:
        """Test with string client type."""
        config = RateLimitConfig()
        limiter: InMemoryRateLimiter[str] = InMemoryRateLimiter(config)
        limit = RateLimit(requests=10, window=timedelta(minutes=1))

        result = await limiter.check("user_123", limit)

        assert result.client == "user_123"
        assert isinstance(result.client, str)

    @pytest.mark.asyncio
    async def test_int_client(self) -> None:
        """Test with integer client type."""
        config = RateLimitConfig()
        limiter: InMemoryRateLimiter[int] = InMemoryRateLimiter(config)
        limit = RateLimit(requests=10, window=timedelta(minutes=1))

        result = await limiter.check(12345, limit)

        assert result.client == 12345
        assert isinstance(result.client, int)

    @pytest.mark.asyncio
    async def test_uuid_client(self) -> None:
        """Test with UUID client type."""
        from uuid import UUID, uuid4

        config = RateLimitConfig()
        limiter: InMemoryRateLimiter[UUID] = InMemoryRateLimiter(config)
        limit = RateLimit(requests=10, window=timedelta(minutes=1))

        client_id = uuid4()
        result = await limiter.check(client_id, limit)

        assert result.client == client_id
        assert isinstance(result.client, UUID)
