"""Elasticsearch core components.

Contains client, configuration, and document definitions.

**Feature: infrastructure-restructuring-2025**
"""

from infrastructure.elasticsearch.core.client import ElasticsearchClient
from infrastructure.elasticsearch.core.config import ElasticsearchConfig
from infrastructure.elasticsearch.core.document import Document

__all__ = [
    "ElasticsearchClient",
    "ElasticsearchConfig",
    "Document",
]
