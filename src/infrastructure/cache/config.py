"""Cache configuration.

**Feature: python-api-base-2025-state-of-art**
**Validates: Requirements 4.1**
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CacheConfig:
    """Configuration for cache providers.

    Attributes:
        default_ttl: Default time-to-live in seconds.
        max_size: Maximum number of entries.
        prefix: Key prefix for namespacing.
        key_prefix: Alias for prefix.
        serializer: Serializer type to use.
    """

    default_ttl: int = 3600
    max_size: int = 10000
    prefix: str = ""
    key_prefix: str = ""
    serializer: str = "json"

    # Redis-specific settings
    redis_url: str | None = None
    redis_db: int = 0
    redis_password: str | None = None

    # Connection pool settings
    pool_min_size: int = 1
    pool_max_size: int = 10

    # Additional options
    options: dict[str, Any] = field(default_factory=dict)
