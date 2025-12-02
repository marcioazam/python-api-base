"""Generic Elasticsearch infrastructure.

Provides type-safe Elasticsearch operations with PEP 695 generics.

**Feature: observability-infrastructure**
**Requirement: R2 - Generic Elasticsearch Client**
"""

from infrastructure.elasticsearch.client import (
    ElasticsearchClient,
    ElasticsearchClientConfig,
)
from infrastructure.elasticsearch.repository import (
    ElasticsearchRepository,
    SearchQuery,
    SearchResult,
    AggregationResult,
)
from infrastructure.elasticsearch.document import (
    ElasticsearchDocument,
    DocumentMetadata,
)

__all__ = [
    # Client
    "ElasticsearchClient",
    "ElasticsearchClientConfig",
    # Repository
    "ElasticsearchRepository",
    "SearchQuery",
    "SearchResult",
    "AggregationResult",
    # Document
    "ElasticsearchDocument",
    "DocumentMetadata",
]
