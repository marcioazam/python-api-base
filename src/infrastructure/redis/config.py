"""Redis configuration.

**Feature: enterprise-infrastructure-2025**
**Requirement: R1 - Redis Distributed Cache**
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class RedisConfig:
    """Configuration for Redis client.

    **Requirement: R1.1 - Connection pool with configurable size and timeout**

    Attributes:
        url: Redis connection URL
        host: Redis host (used if url not provided)
        port: Redis port
        db: Redis database number
        password: Redis password
        ssl: Enable SSL/TLS
        pool_min_size: Minimum connection pool size
        pool_max_size: Maximum connection pool size
        connect_timeout: Connection timeout in seconds
        socket_timeout: Socket operation timeout in seconds
        retry_on_timeout: Retry on timeout
        key_prefix: Prefix for all keys
        default_ttl: Default TTL in seconds
        enable_fallback: Enable local cache fallback
        circuit_breaker_threshold: Failures before opening circuit
        circuit_breaker_timeout: Seconds to wait before retry
    """

    url: str | None = None
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: str | None = None
    ssl: bool = False

    # Connection pool
    pool_min_size: int = 1
    pool_max_size: int = 10
    connect_timeout: float = 5.0
    socket_timeout: float = 5.0
    retry_on_timeout: bool = True

    # Cache settings
    key_prefix: str = ""
    default_ttl: int = 3600

    # Resilience
    enable_fallback: bool = True
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: float = 30.0

    def get_url(self) -> str:
        """Get Redis connection URL.

        Returns:
            Redis URL string
        """
        if self.url:
            return self.url

        scheme = "rediss" if self.ssl else "redis"
        auth = f":{self.password}@" if self.password else ""
        return f"{scheme}://{auth}{self.host}:{self.port}/{self.db}"

    def to_connection_kwargs(self) -> dict[str, Any]:
        """Get kwargs for redis connection.

        Returns:
            Connection kwargs dictionary
        """
        return {
            "socket_connect_timeout": self.connect_timeout,
            "socket_timeout": self.socket_timeout,
            "retry_on_timeout": self.retry_on_timeout,
            "max_connections": self.pool_max_size,
        }
