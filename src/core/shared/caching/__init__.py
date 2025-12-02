"""Multi-level caching system with LRU eviction and TTL support.

**Feature: code-review-refactoring, Task 17.2: Refactor caching.py**
**Validates: Requirements 5.5**

Note: Cache implementations are in infrastructure/cache/.
This module re-exports for convenience.
"""

from infrastructure.cache.config import CacheConfig
from infrastructure.cache.policies import CacheEntry
from infrastructure.cache.decorators import cached, get_default_cache
from infrastructure.cache.providers import (
    InMemoryCacheProvider,
    RedisCacheProvider,
)

from .utils import generate_cache_key

__all__ = [
    "CacheConfig",
    "CacheEntry",
    "InMemoryCacheProvider",
    "RedisCacheProvider",
    "cached",
    "generate_cache_key",
    "get_default_cache",
]
