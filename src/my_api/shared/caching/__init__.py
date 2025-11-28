"""Multi-level caching system with LRU eviction and TTL support.

This package provides a flexible caching infrastructure with:
- In-memory cache with LRU eviction
- Redis cache with JSON serialization
- Configurable TTL (time-to-live)
- Thread-safe async operations
- Graceful degradation on failures

**Feature: advanced-reusability**
**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7**
"""

from .config import CacheConfig, CacheEntry
from .decorators import cached, get_default_cache
from .providers import InMemoryCacheProvider, RedisCacheProvider
from .utils import generate_cache_key

__all__ = [
    # Config
    "CacheConfig",
    "CacheEntry",
    # Providers
    "InMemoryCacheProvider",
    "RedisCacheProvider",
    # Decorators
    "cached",
    "get_default_cache",
    # Utils
    "generate_cache_key",
]
