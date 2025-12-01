"""Rate limit storage backends.

**Feature: code-review-refactoring, Task 18.2: Refactor tiered_rate_limiter.py**
**Validates: Requirements 5.8**
"""

import asyncio
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Protocol


class RateLimitStore(Protocol):
    """Protocol for rate limit storage backends."""

    async def get_count(self, key: str, window: int) -> int:
        """Get current count for a key within a time window."""
        ...

    async def increment(self, key: str, window: int, amount: int = 1) -> int:
        """Increment count for a key and return new value."""
        ...

    async def reset(self, key: str) -> None:
        """Reset count for a key."""
        ...

    async def get_ttl(self, key: str) -> int:
        """Get time-to-live for a key in seconds."""
        ...


@dataclass
class InMemoryRateLimitStore:
    """In-memory rate limit store for development/testing."""

    _counts: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    _timestamps: dict[str, float] = field(default_factory=dict)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def get_count(self, key: str, window: int) -> int:
        """Get current count for a key within a time window."""
        async with self._lock:
            now = time.time()
            timestamp = self._timestamps.get(key, now)

            if now - timestamp >= window:
                self._counts[key] = 0
                self._timestamps[key] = now

            return self._counts[key]

    async def increment(self, key: str, window: int, amount: int = 1) -> int:
        """Increment count for a key and return new value."""
        async with self._lock:
            now = time.time()
            timestamp = self._timestamps.get(key, now)

            if now - timestamp >= window:
                self._counts[key] = 0
                self._timestamps[key] = now

            self._counts[key] += amount
            return self._counts[key]

    async def reset(self, key: str) -> None:
        """Reset count for a key."""
        async with self._lock:
            self._counts[key] = 0
            self._timestamps.pop(key, None)

    async def get_ttl(self, key: str) -> int:
        """Get time-to-live for a key in seconds."""
        async with self._lock:
            timestamp = self._timestamps.get(key)
            if timestamp is None:
                return 0
            elapsed = time.time() - timestamp
            return max(0, int(60 - elapsed))
