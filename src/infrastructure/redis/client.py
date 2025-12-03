"""Redis client with circuit breaker and Pydantic support.

Main client interface that composes connection and operations management.

**Feature: enterprise-infrastructure-2025**
**Requirement: R1 - Redis Distributed Cache**
**Refactored: 2025 - Split into modular components for maintainability**
"""

from __future__ import annotations

from typing import Any, TypeVar, Generic
from collections.abc import Sequence

from pydantic import BaseModel

from infrastructure.redis.config import RedisConfig
from infrastructure.redis.circuit_breaker import CircuitBreaker
from infrastructure.redis.connection import RedisConnection
from infrastructure.redis.operations import RedisOperations

T = TypeVar("T")


class RedisClient(Generic[T]):
    """Enterprise Redis client with circuit breaker.

    **Feature: enterprise-infrastructure-2025**
    **Requirement: R1 - Redis Distributed Cache**

    Features:
    - Connection pooling
    - Circuit breaker pattern
    - Automatic fallback to local cache
    - Pydantic model serialization
    - Bulk operations

    Example:
        >>> config = RedisConfig(host="localhost", port=6379)
        >>> async with RedisClient(config) as client:
        ...     await client.set("key", {"name": "John"})
        ...     value = await client.get("key")
    """

    def __init__(self, config: RedisConfig | None = None) -> None:
        """Initialize Redis client.

        Args:
            config: Redis configuration
        """
        self._config = config or RedisConfig()
        self._circuit = CircuitBreaker(
            failure_threshold=self._config.circuit_breaker_threshold,
            reset_timeout=self._config.circuit_breaker_timeout,
        )
        self._connection = RedisConnection(self._config, self._circuit)
        self._operations = RedisOperations[T](self._connection)

    async def __aenter__(self) -> "RedisClient[T]":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.close()

    async def connect(self) -> bool:
        """Establish Redis connection.

        **Requirement: R1.1 - Connection pool with configurable size**

        Returns:
            True if connected successfully
        """
        return await self._connection.connect()

    async def close(self) -> None:
        """Close Redis connection."""
        await self._connection.close()

    # =========================================================================
    # Core Operations (delegated to operations)
    # =========================================================================

    async def get(
        self,
        key: str,
        model: type[BaseModel] | None = None,
    ) -> T | None:
        """Get value from cache.

        **Requirement: R1.2 - Get operation with typed responses**

        Args:
            key: Cache key
            model: Optional Pydantic model for deserialization

        Returns:
            Cached value or None
        """
        return await self._operations.get(key, model)

    async def set(
        self,
        key: str,
        value: T,
        ttl: int | None = None,
    ) -> bool:
        """Set value in cache.

        **Requirement: R1.2 - Set operation**
        **Requirement: R1.3 - TTL parameter with automatic expiration**

        Args:
            key: Cache key
            value: Value to cache
            ttl: TTL in seconds (uses default if None)

        Returns:
            True if successful
        """
        return await self._operations.set(key, value, ttl)

    async def delete(self, key: str) -> bool:
        """Delete value from cache.

        **Requirement: R1.2 - Delete operation**

        Args:
            key: Cache key

        Returns:
            True if key was deleted
        """
        return await self._operations.delete(key)

    async def exists(self, key: str) -> bool:
        """Check if key exists.

        **Requirement: R1.2 - Exists operation**

        Args:
            key: Cache key

        Returns:
            True if key exists
        """
        return await self._operations.exists(key)

    # =========================================================================
    # Bulk Operations (delegated to operations)
    # =========================================================================

    async def get_many(
        self,
        keys: Sequence[str],
        model: type[BaseModel] | None = None,
    ) -> dict[str, T]:
        """Get multiple values.

        Args:
            keys: Cache keys
            model: Optional Pydantic model for deserialization

        Returns:
            Dictionary of key -> value
        """
        return await self._operations.get_many(keys, model)

    async def set_many(
        self,
        items: dict[str, T],
        ttl: int | None = None,
    ) -> bool:
        """Set multiple values.

        Args:
            items: Dictionary of key -> value
            ttl: TTL in seconds

        Returns:
            True if successful
        """
        return await self._operations.set_many(items, ttl)

    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern.

        **Requirement: R1.7 - Bulk invalidation using pattern matching**

        Args:
            pattern: Key pattern (e.g., "user:*")

        Returns:
            Number of keys deleted
        """
        return await self._operations.delete_pattern(pattern)

    # =========================================================================
    # Health & Stats (delegated to connection)
    # =========================================================================

    async def ping(self) -> bool:
        """Check Redis connectivity.

        Returns:
            True if Redis is reachable
        """
        if not self._connection.is_connected:
            return False

        try:
            await self._connection.client.ping()
            return True
        except Exception:
            return False

    @property
    def circuit_state(self) -> str:
        """Get circuit breaker state."""
        return self._circuit.state.value

    @property
    def is_connected(self) -> bool:
        """Check if connected to Redis."""
        return self._connection.is_connected

    @property
    def is_using_fallback(self) -> bool:
        """Check if currently using fallback cache."""
        return not self._connection.is_connected or self._circuit.is_open
