"""Cache infrastructure.

**Refactored: 2025 - Split into focused modules**
"""

from infrastructure.cache.local_cache import LRUCache
from infrastructure.cache.memory_provider import InMemoryCacheProvider
from infrastructure.cache.models import CacheStats
from infrastructure.cache.protocols import (
    CacheEntry,
    CacheKey,
    CacheProvider,
    JsonSerializer,
)
from infrastructure.cache.redis_provider import RedisCacheProvider

__all__ = [
    "CacheEntry",
    "CacheKey",
    "CacheProvider",
    "CacheStats",
    "InMemoryCacheProvider",
    "JsonSerializer",
    "LRUCache",
    "RedisCacheProvider",
]
