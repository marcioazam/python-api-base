"""Cache configuration and entry models.

**Feature: code-review-refactoring, Task 17.2: Refactor caching.py**
**Validates: Requirements 5.5**
"""

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CacheConfig:
    """Configuration for cache providers.

    Attributes:
        ttl: Default time-to-live in seconds. None for no expiration.
        max_size: Maximum number of entries (for in-memory cache).
        key_prefix: Prefix for all cache keys.
    """

    ttl: int | None = 3600
    max_size: int = 1000
    key_prefix: str = ""


@dataclass
class CacheEntry:
    """A single cache entry with expiration tracking.

    Attributes:
        value: The cached value.
        created_at: Unix timestamp when entry was created.
        ttl: Time-to-live in seconds. None for no expiration.
    """

    value: Any
    created_at: float = field(default_factory=time.time)
    ttl: int | None = None

    @property
    def is_expired(self) -> bool:
        """Check if this entry has expired."""
        if self.ttl is None:
            return False
        return time.time() - self.created_at > self.ttl

    @property
    def remaining_ttl(self) -> int | None:
        """Get remaining TTL in seconds."""
        if self.ttl is None:
            return None
        remaining = self.ttl - (time.time() - self.created_at)
        return max(0, int(remaining))
