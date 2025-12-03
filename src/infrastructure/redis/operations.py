"""Redis operations (core and bulk).

**Feature: enterprise-infrastructure-2025**
**Requirement: R1.2 - Core Operations**
"""

from __future__ import annotations

import logging
from typing import TypeVar, Generic
from collections.abc import Sequence

from pydantic import BaseModel

from infrastructure.redis.connection import RedisConnection

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RedisOperations(Generic[T]):
    """Handles Redis core and bulk operations with circuit breaker.

    **Feature: enterprise-infrastructure-2025**
    **Requirement: R1.2 - Core Operations (get, set, delete, exists)**
    """

    def __init__(self, connection: RedisConnection) -> None:
        """Initialize operations handler.

        Args:
            connection: Redis connection instance
        """
        self._conn = connection

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
        if await self._conn.use_fallback():
            return (
                await self._conn.fallback.get(key) if self._conn.fallback else None
            )

        try:
            full_key = self._conn.make_key(key)
            data = await self._conn.client.get(full_key)
            await self._conn.circuit_breaker.record_success()
            return self._conn.deserialize(data, model)

        except Exception as e:
            logger.warning(f"Redis get failed: {e}", extra={"key": key})
            await self._conn.circuit_breaker.record_failure(e)

            if self._conn.fallback:
                return await self._conn.fallback.get(key)
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
        if await self._conn.use_fallback():
            if self._conn.fallback:
                await self._conn.fallback.set(key, value, ttl)
                return True
            return False

        try:
            full_key = self._conn.make_key(key)
            data = self._conn.serialize(value)
            effective_ttl = (
                ttl if ttl is not None else self._conn._config.default_ttl
            )

            if effective_ttl:
                await self._conn.client.setex(full_key, effective_ttl, data)
            else:
                await self._conn.client.set(full_key, data)

            await self._conn.circuit_breaker.record_success()

            # Also set in fallback for faster reads
            if self._conn.fallback:
                await self._conn.fallback.set(key, value, ttl)

            return True

        except Exception as e:
            logger.warning(f"Redis set failed: {e}", extra={"key": key})
            await self._conn.circuit_breaker.record_failure(e)

            if self._conn.fallback:
                await self._conn.fallback.set(key, value, ttl)
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
        if await self._conn.use_fallback():
            return (
                await self._conn.fallback.delete(key)
                if self._conn.fallback
                else False
            )

        try:
            full_key = self._conn.make_key(key)
            result = await self._conn.client.delete(full_key)
            await self._conn.circuit_breaker.record_success()

            if self._conn.fallback:
                await self._conn.fallback.delete(key)

            return result > 0

        except Exception as e:
            logger.warning(f"Redis delete failed: {e}", extra={"key": key})
            await self._conn.circuit_breaker.record_failure(e)

            if self._conn.fallback:
                return await self._conn.fallback.delete(key)
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists.

        **Requirement: R1.2 - Exists operation**

        Args:
            key: Cache key

        Returns:
            True if key exists
        """
        if await self._conn.use_fallback():
            return (
                await self._conn.fallback.exists(key)
                if self._conn.fallback
                else False
            )

        try:
            full_key = self._conn.make_key(key)
            result = await self._conn.client.exists(full_key)
            await self._conn.circuit_breaker.record_success()
            return result > 0

        except Exception as e:
            logger.warning(f"Redis exists failed: {e}", extra={"key": key})
            await self._conn.circuit_breaker.record_failure(e)

            if self._conn.fallback:
                return await self._conn.fallback.exists(key)
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
        if await self._conn.use_fallback():
            result = {}
            if self._conn.fallback:
                for key in keys:
                    value = await self._conn.fallback.get(key)
                    if value is not None:
                        result[key] = value
            return result

        try:
            full_keys = [self._conn.make_key(k) for k in keys]
            values = await self._conn.client.mget(full_keys)
            await self._conn.circuit_breaker.record_success()

            result = {}
            for key, value in zip(keys, values, strict=False):
                if value is not None:
                    deserialized = self._conn.deserialize(value, model)
                    if deserialized is not None:
                        result[key] = deserialized

            return result

        except Exception as e:
            logger.warning(f"Redis mget failed: {e}")
            await self._conn.circuit_breaker.record_failure(e)
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
        if await self._conn.use_fallback():
            if self._conn.fallback:
                for key, value in items.items():
                    await self._conn.fallback.set(key, value, ttl)
                return True
            return False

        try:
            pipe = self._conn.client.pipeline()
            effective_ttl = (
                ttl if ttl is not None else self._conn._config.default_ttl
            )

            for key, value in items.items():
                full_key = self._conn.make_key(key)
                data = self._conn.serialize(value)
                if effective_ttl:
                    pipe.setex(full_key, effective_ttl, data)
                else:
                    pipe.set(full_key, data)

            await pipe.execute()
            await self._conn.circuit_breaker.record_success()
            return True

        except Exception as e:
            logger.warning(f"Redis mset failed: {e}")
            await self._conn.circuit_breaker.record_failure(e)
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern.

        **Requirement: R1.7 - Bulk invalidation using pattern matching**

        Args:
            pattern: Key pattern (e.g., "user:*")

        Returns:
            Number of keys deleted
        """
        if await self._conn.use_fallback():
            return (
                await self._conn.fallback.clear_pattern(pattern)
                if self._conn.fallback
                else 0
            )

        try:
            full_pattern = self._conn.make_key(pattern)
            cursor = 0
            deleted = 0

            while True:
                cursor, keys = await self._conn.client.scan(
                    cursor,
                    match=full_pattern,
                    count=100,
                )
                if keys:
                    deleted += await self._conn.client.delete(*keys)
                if cursor == 0:
                    break

            await self._conn.circuit_breaker.record_success()
            logger.info(
                f"Pattern delete completed",
                extra={"pattern": pattern, "deleted": deleted},
            )
            return deleted

        except Exception as e:
            logger.warning(f"Redis pattern delete failed: {e}")
            await self._conn.circuit_breaker.record_failure(e)
            return 0
