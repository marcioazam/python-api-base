"""Redis connection and serialization management.

**Feature: enterprise-infrastructure-2025**
**Requirement: R1.1 - Connection Management**
"""

from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import BaseModel

from infrastructure.redis.config import RedisConfig
from infrastructure.redis.circuit_breaker import CircuitBreaker
from infrastructure.cache.providers import InMemoryCacheProvider

logger = logging.getLogger(__name__)


class RedisConnection:
    """Manages Redis connection lifecycle and fallback logic.

    **Feature: enterprise-infrastructure-2025**
    **Requirement: R1.1 - Connection pool with configurable size**
    """

    def __init__(
        self,
        config: RedisConfig | None = None,
        circuit_breaker: CircuitBreaker | None = None,
    ) -> None:
        """Initialize Redis connection manager.

        Args:
            config: Redis configuration
            circuit_breaker: Circuit breaker instance
        """
        self._config = config or RedisConfig()
        self._redis: Any = None
        self._connected = False
        self._circuit = circuit_breaker or CircuitBreaker(
            failure_threshold=self._config.circuit_breaker_threshold,
            reset_timeout=self._config.circuit_breaker_timeout,
        )
        self._fallback: InMemoryCacheProvider | None = None

        if self._config.enable_fallback:
            from infrastructure.cache.config import CacheConfig

            self._fallback = InMemoryCacheProvider(
                CacheConfig(
                    default_ttl=self._config.default_ttl,
                    key_prefix=self._config.key_prefix,
                )
            )

    @property
    def client(self) -> Any:
        """Get the Redis client."""
        return self._redis

    @property
    def is_connected(self) -> bool:
        """Check if connected to Redis."""
        return self._connected

    @property
    def fallback(self) -> InMemoryCacheProvider | None:
        """Get the fallback cache provider."""
        return self._fallback

    @property
    def circuit_breaker(self) -> CircuitBreaker:
        """Get the circuit breaker."""
        return self._circuit

    async def connect(self) -> bool:
        """Establish Redis connection.

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

    async def use_fallback(self) -> bool:
        """Check if should use fallback cache.

        Returns:
            True if fallback should be used
        """
        if not self._config.enable_fallback or self._fallback is None:
            return False

        if not self._connected:
            return True

        return not await self._circuit.can_execute()

    def make_key(self, key: str) -> str:
        """Create full cache key with prefix.

        Args:
            key: Base key

        Returns:
            Full key with prefix
        """
        if self._config.key_prefix:
            return f"{self._config.key_prefix}:{key}"
        return key

    @staticmethod
    def serialize(value: Any) -> str:
        """Serialize value to JSON string.

        **Requirement: R1.6 - JSON serialization with Pydantic support**

        Args:
            value: Value to serialize

        Returns:
            JSON string
        """
        if isinstance(value, BaseModel):
            return value.model_dump_json()
        return json.dumps(value, default=str)

    @staticmethod
    def deserialize(
        data: str | None, model: type[BaseModel] | None = None
    ) -> Any:
        """Deserialize JSON string to value.

        **Requirement: R1.6 - Pydantic model support**

        Args:
            data: JSON string
            model: Optional Pydantic model for deserialization

        Returns:
            Deserialized value or None
        """
        if data is None:
            return None

        try:
            if model is not None and issubclass(model, BaseModel):
                return model.model_validate_json(data)
            return json.loads(data)
        except (json.JSONDecodeError, ValueError):
            return None
