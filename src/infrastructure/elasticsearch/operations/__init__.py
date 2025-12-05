"""Elasticsearch operations.

Contains query, index, search, and repository operations.

**Feature: infrastructure-restructuring-2025**
"""

from infrastructure.elasticsearch.operations.index_operations import IndexOperations
from infrastructure.elasticsearch.operations.query import QueryBuilder
from infrastructure.elasticsearch.operations.repository import ElasticsearchRepository
from infrastructure.elasticsearch.operations.search_operations import SearchOperations

__all__ = [
    "IndexOperations",
    "QueryBuilder",
    "ElasticsearchRepository",
    "SearchOperations",
]
