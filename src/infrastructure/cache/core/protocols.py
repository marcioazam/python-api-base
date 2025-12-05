"""Cache provider protocols.

**Feature: python-api-base-2025-state-of-art**
**Refactored: 2025 - Extracted from providers.py for SRP compliance**
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from infrastructure.cache.models import CacheStats


@runtime_checkable
class Serializer[T](Protocol):
    """Protocol for type-safe serialization.

    Type Parameters:
        T: The type to serialize/deserialize.
    """

    def serialize(self, value: T) -> bytes:
        """Serialize value to bytes."""
        ...

    def deserialize(self, data: bytes) -> T:
        """Deserialize bytes to value."""
        ...


class JsonSerializer[T]:
    """JSON serializer implementation."""

    def serialize(self, value: T) -> bytes:
        """Serialize value to JSON bytes."""
        return json.dumps(value, default=str).encode("utf-8")

    def deserialize(self, data: bytes) -> T:
        """Deserialize JSON bytes to value."""
        return json.loads(data.decode("utf-8"))


@dataclass(frozen=True, slots=True)
class CacheKey[T]:
    """Type-safe cache key that associates a key pattern with a type.

    Example:
        user_cache: CacheKey[User] = CacheKey("user:{id}")
        key = user_cache.format(id="123")  # "user:123"
    """

    pattern: str

    def format(self, **kwargs: Any) -> str:
        """Format the key pattern with provided values."""
        return self.pattern.format(**kwargs)

    def __str__(self) -> str:
        """Return the pattern string."""
        return self.pattern


@dataclass(frozen=True, slots=True)
class CacheEntry[T]:
    """A single cache entry with expiration tracking.

    Attributes:
        key: The cache key.
        value: The cached value of type T.
        created_at: When entry was created.
        ttl: Time-to-live in seconds.
        expires_at: When entry expires.
        tags: Tuple of tags for group invalidation.
    """

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


class CacheProvider[T](Protocol):
    """Protocol for cache providers with PEP 695 generics."""

    async def get(self, key: str) -> T | None:
        """Retrieve a value from the cache."""
        ...

    async def set(self, key: str, value: T, ttl: int | None = None) -> None:
        """Store a value in the cache."""
        ...

    async def delete(self, key: str) -> bool:
        """Remove a value from the cache."""
        ...

    async def exists(self, key: str) -> bool:
        """Check if a key exists in the cache."""
        ...

    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern."""
        ...

    async def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        ...
