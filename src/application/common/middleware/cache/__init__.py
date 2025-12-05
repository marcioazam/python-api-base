"""Cache middleware and utilities.

Provides caching functionality for query results and cache invalidation strategies.

**Feature: application-layer-improvements-2025**
"""

from application.common.middleware.cache.cache_invalidation import (
    CacheInvalidationStrategy,
    CompositeCacheInvalidationStrategy,
    InvalidationRule,
    ItemCacheInvalidationStrategy,
    UserCacheInvalidationStrategy,
)
from application.common.middleware.cache.query_cache import (
    InMemoryQueryCache,
    QueryCache,
)

__all__ = [
    "CacheInvalidationStrategy",
    "CompositeCacheInvalidationStrategy",
    "InMemoryQueryCache",
    "InvalidationRule",
    "ItemCacheInvalidationStrategy",
    "QueryCache",
    "UserCacheInvalidationStrategy",
]
