"""Search service with Elasticsearch support and PEP 695 generics.

**Feature: enterprise-features-2025, Task 7.1**
**Validates: Requirements 7.8, 7.9**
"""

from .models import Indexer, SearchProvider, SearchQuery, SearchResult
from .service import InMemorySearchProvider, SearchService

__all__ = [
    "InMemorySearchProvider",
    "Indexer",
    "SearchProvider",
    "SearchQuery",
    "SearchResult",
    "SearchService",
]
