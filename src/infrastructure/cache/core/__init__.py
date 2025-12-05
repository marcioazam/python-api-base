"""Cache core components.

Contains cache configuration, models, protocols, policies, and serializers.

**Feature: infrastructure-restructuring-2025**
"""

from infrastructure.cache.core.config import CacheConfig
from infrastructure.cache.core.models import CacheEntry
from infrastructure.cache.core.policies import CachePolicy
from infrastructure.cache.core.protocols import CacheProvider
from infrastructure.cache.core.serializers import CacheSerializer

__all__ = [
    "CacheConfig",
    "CacheEntry",
    "CachePolicy",
    "CacheProvider",
    "CacheSerializer",
]
