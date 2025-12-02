"""Redis client with circuit breaker and Pydantic support.

**Feature: enterprise-infrastructure-2025**
**Requirement: R1 - Redis Distributed Cache**
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, TypeVar, Generic
from collections.abc import Sequence

from pydantic import BaseModel

from infrastructure.redis.config import RedisConfig
from infrastructure.redis.circuit_breaker import CircuitBreaker, CircuitOpenError
from infrastructure.cache.providers import InMemoryCacheProvider

logger = logging.getLogger(__name__)

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
        self._redis: Any = None
        self._connected = False
        self._circuit = CircuitBreaker(
            failure_threshold=self._config.circuit_breaker_threshold,
            reset_timeout=self._config.circuit_breaker_timeout,
        )
        self._fallback: InMemoryCacheProvider[T] | None = None

        if self._config.enable_fallback:
            from infrastructure.cache.config import CacheConfig

            self._fallback = InMemoryCacheProvider(
                CacheConfig(
                    default_ttl=self._config.default_ttl,
                    key_prefix=self._config.key_prefix,
                )
            )

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
        if self._connected:
            return True

        try:
            import redis.asyncio as redis

            self._redis = redis.from_url(
                self._config.get_url(),
                encoding="utf-8",
                decode_responses=True,
                **self._config.to_connection_kwargs(),
            )
            await self._redis.ping()
            self._connected = True
            logger.info("Redis connected", extra={"url": self._config.host})
            return True

        except ImportError:
            logger.warning("redis package not installed")
            return False
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
            await self._circuit.record_failure(e)
            return False

    async def close(self) -> None:
        """Close Redis connection."""
        if self._redis is not None:
            await self._redis.close()
            self._redis = None
            self._connected = False
            logger.info("Redis connection closed")

    def _make_key(self, key: str) -> str:
        """Create full cache key with prefix."""
        if self._config.key_prefix:
            return f"{self._config.key_prefix}:{key}"
        return key

    def _serialize(self, value: Any) -> str:
        """Serialize value to JSON string.

        **Requirement: R1.6 - JSON serialization with Pydantic support**
        """
        if isinstance(value, BaseModel):
            return value.model_dump_json()
        return json.dumps(value, default=str)

    def _deserialize(self, data: str | None, model: type[BaseModel] | None = None) -> Any:
        """Deserialize JSON string to value.

        **Requirement: R1.6 - Pydantic model support**
        """
        if data is None:
            return None

        try:
            if model is not None and issubclass(model, BaseModel):
                return model.model_validate_json(data)
            return json.loads(data)
        except (json.JSONDecodeError, ValueError):
            return None

    async def _use_fallback(self) -> bool:
        """Check if should use fallback cache."""
        if not self._config.enable_fallback or self._fallback is None:
            return False

        if not self._connected:
            return True

        return not await self._circuit.can_execute()

    # =========================================================================
    # Core Operations
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
        if await self._use_fallback():
            return await self._fallback.get(key) if self._fallback else None

        try:
            full_key = self._make_key(key)
            data = await self._redis.get(full_key)
            await self._circuit.record_success()
            return self._deserialize(data, model)

        except Exception as e:
            logger.warning(f"Redis get failed: {e}", extra={"key": key})
            await self._circuit.record_failure(e)

            if self._fallback:
                return await self._fallback.get(key)
            return None

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
        if await self._use_fallback():
            if self._fallback:
                await self._fallback.set(key, value, ttl)
                return True
            return False

        try:
            full_key = self._make_key(key)
            data = self._serialize(value)
            effective_ttl = ttl if ttl is not None else self._config.default_ttl

            if effective_ttl:
                await self._redis.setex(full_key, effective_ttl, data)
            else:
                await self._redis.set(full_key, data)

            await self._circuit.record_success()

            # Also set in fallback for faster reads
            if self._fallback:
                await self._fallback.set(key, value, ttl)

            return True

        except Exception as e:
            logger.warning(f"Redis set failed: {e}", extra={"key": key})
            await self._circuit.record_failure(e)

            if self._fallback:
                await self._fallback.set(key, value, ttl)
                return True
            return False

    async def delete(self, key: str) -> bool:
        """Delete value from cache.

        **Requirement: R1.2 - Delete operation**

        Args:
            key: Cache key

        Returns:
            True if key was deleted
        """
        if await self._use_fallback():
            return await self._fallback.delete(key) if self._fallback else False

        try:
            full_key = self._make_key(key)
            result = await self._redis.delete(full_key)
            await self._circuit.record_success()

            if self._fallback:
                await self._fallback.delete(key)

            return result > 0

        except Exception as e:
            logger.warning(f"Redis delete failed: {e}", extra={"key": key})
            await self._circuit.record_failure(e)

            if self._fallback:
                return await self._fallback.delete(key)
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists.

        **Requirement: R1.2 - Exists operation**

        Args:
            key: Cache key

        Returns:
            True if key exists
        """
        if await self._use_fallback():
            return await self._fallback.exists(key) if self._fallback else False

        try:
            full_key = self._make_key(key)
            result = await self._redis.exists(full_key)
            await self._circuit.record_success()
            return result > 0

        except Exception as e:
            logger.warning(f"Redis exists failed: {e}", extra={"key": key})
            await self._circuit.record_failure(e)

            if self._fallback:
                return await self._fallback.exists(key)
            return False

    # =========================================================================
    # Bulk Operations
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
        if await self._use_fallback():
            result = {}
            if self._fallback:
                for key in keys:
                    value = await self._fallback.get(key)
                    if value is not None:
                        result[key] = value
            return result

        try:
            full_keys = [self._make_key(k) for k in keys]
            values = await self._redis.mget(full_keys)
            await self._circuit.record_success()

            result = {}
            for key, value in zip(keys, values, strict=False):
                if value is not None:
                    deserialized = self._deserialize(value, model)
                    if deserialized is not None:
                        result[key] = deserialized

            return result

        except Exception as e:
            logger.warning(f"Redis mget failed: {e}")
            await self._circuit.record_failure(e)
            return {}

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
        if await self._use_fallback():
            if self._fallback:
                for key, value in items.items():
                    await self._fallback.set(key, value, ttl)
                return True
            return False

        try:
            pipe = self._redis.pipeline()
            effective_ttl = ttl if ttl is not None else self._config.default_ttl

            for key, value in items.items():
                full_key = self._make_key(key)
                data = self._serialize(value)
                if effective_ttl:
                    pipe.setex(full_key, effective_ttl, data)
                else:
                    pipe.set(full_key, data)

            await pipe.execute()
            await self._circuit.record_success()
            return True

        except Exception as e:
            logger.warning(f"Redis mset failed: {e}")
            await self._circuit.record_failure(e)
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern.

        **Requirement: R1.7 - Bulk invalidation using pattern matching**

        Args:
            pattern: Key pattern (e.g., "user:*")

        Returns:
            Number of keys deleted
        """
        if await self._use_fallback():
            return await self._fallback.clear_pattern(pattern) if self._fallback else 0

        try:
            full_pattern = self._make_key(pattern)
            cursor = 0
            deleted = 0

            while True:
                cursor, keys = await self._redis.scan(
                    cursor,
                    match=full_pattern,
                    count=100,
                )
                if keys:
                    deleted += await self._redis.delete(*keys)
                if cursor == 0:
                    break

            await self._circuit.record_success()
            logger.info(
                f"Pattern delete completed",
                extra={"pattern": pattern, "deleted": deleted},
            )
            return deleted

        except Exception as e:
            logger.warning(f"Redis pattern delete failed: {e}")
            await self._circuit.record_failure(e)
            return 0

    # =========================================================================
    # Health & Stats
    # =========================================================================

    async def ping(self) -> bool:
        """Check Redis connectivity.

        Returns:
            True if Redis is reachable
        """
        if not self._connected:
            return False

        try:
            await self._redis.ping()
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
        return self._connected

    @property
    def is_using_fallback(self) -> bool:
        """Check if currently using fallback cache."""
        return not self._connected or self._circuit.is_open
