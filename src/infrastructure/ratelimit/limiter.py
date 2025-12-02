"""Generic rate limiter with PEP 695 type parameters.

**Feature: enterprise-generics-2025**
**Requirement: R5 - Generic Rate Limiter**
"""

from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, UTC
from typing import Any, Hashable, Protocol, runtime_checkable

from infrastructure.ratelimit.config import RateLimit, RateLimitConfig


# =============================================================================
# Type Parameters (PEP 695)
# =============================================================================


@runtime_checkable
class ClientIdentifier(Protocol):
    """Protocol for client identifier types.

    **Requirement: R5.1 - TClient represents client identifier type**
    """

    def __hash__(self) -> int:
        """Must be hashable."""
        ...

    def __str__(self) -> str:
        """Must be string-convertible for Redis keys."""
        ...


# =============================================================================
# Result Types
# =============================================================================


@dataclass(frozen=True, slots=True)
class RateLimitResult[TClient]:
    """Rate limit check result with typed client.

    **Requirement: R5.2, R5.3 - Typed RateLimitResult[TClient]**

    Type Parameters:
        TClient: Client identifier type.

    Attributes:
        client: The client identifier.
        is_allowed: Whether the request is allowed.
        remaining: Remaining requests in window.
        limit: Total limit for window.
        reset_at: When the window resets.
        retry_after: Time to wait if rate limited.
    """

    client: TClient
    is_allowed: bool
    remaining: int
    limit: int
    reset_at: datetime
    retry_after: timedelta | None = None

    @property
    def headers(self) -> dict[str, str]:
        """Get rate limit headers for HTTP response.

        Returns:
            Dictionary of rate limit headers.
        """
        headers = {
            "X-RateLimit-Limit": str(self.limit),
            "X-RateLimit-Remaining": str(max(0, self.remaining)),
            "X-RateLimit-Reset": str(int(self.reset_at.timestamp())),
        }
        if self.retry_after:
            headers["Retry-After"] = str(int(self.retry_after.total_seconds()))
        return headers


# =============================================================================
# Abstract Rate Limiter
# =============================================================================


class RateLimiter[TClient: Hashable](ABC):
    """Abstract generic rate limiter.

    **Requirement: R5.1 - Generic_RateLimiter[TClient]**

    Type Parameters:
        TClient: Client identifier type (str, UUID, or custom).

    Example:
        ```python
        limiter: RateLimiter[str] = SlidingWindowLimiter(config)
        result = await limiter.check("user_123", RateLimit(100, timedelta(minutes=1)))
        if not result.is_allowed:
            raise RateLimitExceeded(result)
        ```
    """

    def __init__(self, config: RateLimitConfig) -> None:
        """Initialize rate limiter.

        Args:
            config: Rate limiter configuration.
        """
        self._config = config
        self._limits: dict[str, RateLimit] = {}

    @abstractmethod
    async def check(
        self,
        client: TClient,
        limit: RateLimit,
        endpoint: str = "default",
    ) -> RateLimitResult[TClient]:
        """Check if request is allowed under rate limit.

        **Requirement: R5.2 - check() returns typed RateLimitResult[TClient]**

        Args:
            client: Client identifier.
            limit: Rate limit to apply.
            endpoint: Endpoint identifier for per-endpoint limits.

        Returns:
            RateLimitResult with allow/deny decision.
        """
        ...

    @abstractmethod
    async def reset(self, client: TClient, endpoint: str = "default") -> bool:
        """Reset rate limit for client.

        Args:
            client: Client identifier.
            endpoint: Endpoint identifier.

        Returns:
            True if reset was successful.
        """
        ...

    def configure(self, limits: dict[str, RateLimit]) -> None:
        """Configure per-endpoint limits.

        **Requirement: R5.6 - Per-endpoint limit configuration**

        Args:
            limits: Dictionary mapping endpoint names to limits.
        """
        self._limits.update(limits)

    def get_limit(self, endpoint: str) -> RateLimit:
        """Get limit for endpoint.

        Args:
            endpoint: Endpoint identifier.

        Returns:
            RateLimit for endpoint or default.
        """
        return self._limits.get(endpoint, self._config.default_limit)


# =============================================================================
# In-Memory Implementation (Testing/Development)
# =============================================================================


@dataclass
class _WindowState:
    """Internal state for sliding window."""

    count: int = 0
    window_start: float = field(default_factory=time.time)


class InMemoryRateLimiter[TClient: Hashable](RateLimiter[TClient]):
    """In-memory rate limiter for testing and development.

    Uses sliding window algorithm without Redis.

    Type Parameters:
        TClient: Client identifier type.
    """

    def __init__(self, config: RateLimitConfig) -> None:
        """Initialize in-memory limiter."""
        super().__init__(config)
        self._windows: dict[str, _WindowState] = defaultdict(_WindowState)
        self._lock = asyncio.Lock()

    async def check(
        self,
        client: TClient,
        limit: RateLimit,
        endpoint: str = "default",
    ) -> RateLimitResult[TClient]:
        """Check rate limit using in-memory sliding window."""
        key = f"{endpoint}:{client}"
        now = time.time()
        window_seconds = limit.window_seconds

        async with self._lock:
            state = self._windows[key]

            # Check if window has expired
            if now - state.window_start >= window_seconds:
                state.window_start = now
                state.count = 0

            # Calculate remaining
            remaining = limit.requests - state.count
            reset_at = datetime.fromtimestamp(
                state.window_start + window_seconds, tz=UTC
            )

            if remaining > 0:
                state.count += 1
                return RateLimitResult(
                    client=client,
                    is_allowed=True,
                    remaining=remaining - 1,
                    limit=limit.requests,
                    reset_at=reset_at,
                )
            else:
                retry_after = timedelta(
                    seconds=state.window_start + window_seconds - now
                )
                return RateLimitResult(
                    client=client,
                    is_allowed=False,
                    remaining=0,
                    limit=limit.requests,
                    reset_at=reset_at,
                    retry_after=retry_after,
                )

    async def reset(self, client: TClient, endpoint: str = "default") -> bool:
        """Reset rate limit for client."""
        key = f"{endpoint}:{client}"
        async with self._lock:
            if key in self._windows:
                del self._windows[key]
                return True
            return False


# =============================================================================
# Redis-Backed Sliding Window Implementation
# =============================================================================


class SlidingWindowLimiter[TClient: Hashable](RateLimiter[TClient]):
    """Redis-backed sliding window rate limiter.

    **Requirement: R5.4 - Sliding window algorithm**

    Type Parameters:
        TClient: Client identifier type.

    Uses Redis sorted sets for accurate sliding window implementation.
    Falls back to in-memory if Redis is unavailable.
    """

    def __init__(
        self,
        config: RateLimitConfig,
        redis_client: Any | None = None,
    ) -> None:
        """Initialize Redis-backed limiter.

        Args:
            config: Rate limiter configuration.
            redis_client: Optional Redis client (aioredis.Redis).
        """
        super().__init__(config)
        self._redis = redis_client
        self._fallback = InMemoryRateLimiter[TClient](config)

    async def check(
        self,
        client: TClient,
        limit: RateLimit,
        endpoint: str = "default",
    ) -> RateLimitResult[TClient]:
        """Check rate limit using Redis sliding window.

        Uses ZREMRANGEBYSCORE + ZCARD + ZADD in a pipeline for atomicity.
        """
        if self._redis is None:
            return await self._fallback.check(client, limit, endpoint)

        try:
            return await self._check_redis(client, limit, endpoint)
        except Exception:
            # Fallback to in-memory on Redis errors
            return await self._fallback.check(client, limit, endpoint)

    async def _check_redis(
        self,
        client: TClient,
        limit: RateLimit,
        endpoint: str,
    ) -> RateLimitResult[TClient]:
        """Redis sliding window implementation."""
        key = self._config.get_redis_key(str(client), endpoint)
        now = time.time()
        window_start = now - limit.window_seconds

        # Use pipeline for atomicity
        async with self._redis.pipeline() as pipe:
            # Remove old entries
            pipe.zremrangebyscore(key, 0, window_start)
            # Count current entries
            pipe.zcard(key)
            # Add new entry
            pipe.zadd(key, {str(now): now})
            # Set TTL
            pipe.expire(key, int(limit.window_seconds) + 1)

            results = await pipe.execute()

        current_count = results[1]
        remaining = limit.requests - current_count
        reset_at = datetime.fromtimestamp(now + limit.window_seconds, tz=UTC)

        if current_count < limit.requests:
            return RateLimitResult(
                client=client,
                is_allowed=True,
                remaining=remaining,
                limit=limit.requests,
                reset_at=reset_at,
            )
        else:
            # Find oldest entry to calculate retry_after
            oldest = await self._redis.zrange(key, 0, 0, withscores=True)
            if oldest:
                oldest_time = oldest[0][1]
                retry_seconds = oldest_time + limit.window_seconds - now
            else:
                retry_seconds = limit.window_seconds

            return RateLimitResult(
                client=client,
                is_allowed=False,
                remaining=0,
                limit=limit.requests,
                reset_at=reset_at,
                retry_after=timedelta(seconds=max(0, retry_seconds)),
            )

    async def reset(self, client: TClient, endpoint: str = "default") -> bool:
        """Reset rate limit in Redis."""
        if self._redis is None:
            return await self._fallback.reset(client, endpoint)

        try:
            key = self._config.get_redis_key(str(client), endpoint)
            result = await self._redis.delete(key)
            return result > 0
        except Exception:
            return await self._fallback.reset(client, endpoint)
