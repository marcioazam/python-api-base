"""Cache provider implementations.

**Feature: api-best-practices-review-2025**

Provides cache backends:
- InMemoryCacheProvider: In-memory with LRU/TTL
- RedisCacheProvider: Redis-backed cache
- LRUCache: Generic LRU cache
- RedisCache: Simple Redis cache
- RedisCacheWithJitter: Redis cache with TTL jitter and stampede prevention
"""

from infrastructure.cache.providers.memory import InMemoryCacheProvider
from infrastructure.cache.providers.redis import RedisCacheProvider
from infrastructure.cache.providers.local import LRUCache
from infrastructure.cache.providers.redis_cache import RedisCache, RedisConfig
from infrastructure.cache.providers.redis_jitter import RedisCacheWithJitter
from infrastructure.cache.providers.cache_models import (
    JitterConfig,
    TTLPattern,
    CacheStats,
)

__all__ = [
    "InMemoryCacheProvider",
    "RedisCacheProvider",
    "LRUCache",
    "RedisCache",
    "RedisConfig",
    # Jitter-enabled cache
    "RedisCacheWithJitter",
    "JitterConfig",
    "TTLPattern",
    "CacheStats",
]
