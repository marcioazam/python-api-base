"""Idempotency middleware for command bus.

Prevents duplicate command execution.

**Feature: enterprise-features-2025**
**Validates: Requirements 12.3**
**Refactored: Added runtime_checkable for Protocol validation**
"""

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


@runtime_checkable
class IdempotencyCache(Protocol):
    """Protocol for idempotency cache implementations."""

    async def get(self, key: str) -> Any | None:
        """Get cached result by key."""
        ...

    async def set(self, key: str, value: Any, ttl: int) -> None:
        """Set cached result with TTL in seconds."""
        ...

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        ...


class InMemoryIdempotencyCache:
    """In-memory idempotency cache for development/testing."""

    def __init__(self) -> None:
        self._cache: dict[str, tuple[Any, datetime]] = {}

    async def get(self, key: str) -> Any | None:
        """Get cached result."""
        if key not in self._cache:
            return None

        value, expires_at = self._cache[key]
        if datetime.now(UTC) > expires_at:
            del self._cache[key]
            return None

        return value

    async def set(self, key: str, value: Any, ttl: int) -> None:
        """Set cached result."""
        expires_at = datetime.now(UTC) + timedelta(seconds=ttl)
        self._cache[key] = (value, expires_at)

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        return await self.get(key) is not None

    def cleanup(self) -> int:
        """Remove expired entries. Returns count of removed entries."""
        now = datetime.now(UTC)
        expired = [k for k, (_, exp) in self._cache.items() if now > exp]
        for k in expired:
            del self._cache[k]
        return len(expired)


@dataclass(frozen=True, slots=True)
class IdempotencyConfig:
    """Configuration for idempotency middleware."""

    ttl_seconds: int = 3600
    key_prefix: str = "idempotency"
    header_name: str = "X-Idempotency-Key"


class IdempotencyMiddleware:
    """Middleware that prevents duplicate command execution.

    Uses idempotency keys to detect and prevent duplicate requests.
    Returns cached results for duplicate requests.
    """

    def __init__(
        self,
        cache: IdempotencyCache,
        config: IdempotencyConfig | None = None,
    ) -> None:
        """Initialize idempotency middleware."""
        self._cache = cache
        self._config = config or IdempotencyConfig()

    def _get_idempotency_key(self, command: Any) -> str | None:
        """Extract idempotency key from command."""
        key = getattr(command, "idempotency_key", None)
        if key:
            return str(key)

        get_key = getattr(command, "get_idempotency_key", None)
        if callable(get_key):
            return str(get_key())

        return None

    def _build_cache_key(self, command: Any, idempotency_key: str) -> str:
        """Build full cache key."""
        command_type = type(command).__name__
        return f"{self._config.key_prefix}:{command_type}:{idempotency_key}"

    async def __call__(
        self,
        command: Any,
        next_handler: Callable[[Any], Awaitable[Any]],
    ) -> Any:
        """Execute command with idempotency check."""
        command_type = type(command).__name__
        idempotency_key = self._get_idempotency_key(command)

        if not idempotency_key:
            return await next_handler(command)

        cache_key = self._build_cache_key(command, idempotency_key)

        cached = await self._cache.get(cache_key)
        if cached is not None:
            logger.info(
                f"Returning cached result for {command_type}",
                extra={
                    "command_type": command_type,
                    "idempotency_key": idempotency_key,
                    "operation": "IDEMPOTENCY_HIT",
                },
            )
            return cached

        result = await next_handler(command)

        await self._cache.set(cache_key, result, self._config.ttl_seconds)
        logger.debug(
            f"Cached result for {command_type}",
            extra={
                "command_type": command_type,
                "idempotency_key": idempotency_key,
                "ttl_seconds": self._config.ttl_seconds,
                "operation": "IDEMPOTENCY_CACHE",
            },
        )

        return result
