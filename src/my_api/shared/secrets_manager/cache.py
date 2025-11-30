"""Secrets cache implementations.

**Feature: code-review-refactoring, Task 18.1: Refactor secrets_manager.py**
**Validates: Requirements 5.7**
"""

from datetime import datetime, timedelta, UTC
from typing import Protocol

from .models import SecretValue


class SecretCache(Protocol):
    """Protocol for secret caching."""

    async def get(self, key: str) -> SecretValue | None:
        """Get cached secret."""
        ...

    async def set(self, key: str, value: SecretValue, ttl: int) -> None:
        """Cache secret with TTL."""
        ...

    async def delete(self, key: str) -> None:
        """Remove secret from cache."""
        ...


class InMemorySecretCache:
    """In-memory secret cache for development/testing."""

    def __init__(self) -> None:
        self._cache: dict[str, tuple[SecretValue, datetime]] = {}

    async def get(self, key: str) -> SecretValue | None:
        """Get cached secret if not expired."""
        if key not in self._cache:
            return None

        value, expires_at = self._cache[key]
        if datetime.now(UTC) > expires_at:
            del self._cache[key]
            return None

        return value

    async def set(self, key: str, value: SecretValue, ttl: int) -> None:
        """Cache secret with TTL in seconds."""
        expires_at = datetime.now(UTC) + timedelta(seconds=ttl)
        self._cache[key] = (value, expires_at)

    async def delete(self, key: str) -> None:
        """Remove secret from cache."""
        self._cache.pop(key, None)

    def clear(self) -> None:
        """Clear all cached secrets."""
        self._cache.clear()
