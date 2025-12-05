"""Cache data models.

**Feature: python-api-base-2025-state-of-art**
**Refactored: 2025 - Extracted from providers.py for SRP compliance**
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class CacheKey[T]:
    """Type-safe cache key that associates a key pattern with a type."""

    pattern: str

    def format(self, **kwargs: Any) -> str:
        """Format the key pattern with provided values."""
        return self.pattern.format(**kwargs)

    def __str__(self) -> str:
        """Return the pattern string."""
        return self.pattern


@dataclass(frozen=True, slots=True)
class CacheEntry[T]:
    """A single cache entry with expiration tracking."""

    key: str
    value: T
    created_at: datetime
    ttl: int | None = None
    expires_at: datetime | None = None
    tags: tuple[str, ...] = ()

    @property
    def is_expired(self) -> bool:
        """Check if this entry has expired."""
        if self.expires_at is None:
            return False
        return datetime.now(UTC) > self.expires_at


@dataclass(frozen=True, slots=True)
class CacheStats:
    """Cache statistics for monitoring."""

    hits: int
    misses: int
    hit_rate: float
    memory_usage_bytes: int
    entry_count: int
