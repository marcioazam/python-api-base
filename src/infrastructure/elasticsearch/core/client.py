"""Generic Elasticsearch client with PEP 695 generics.

Provides a type-safe async client for Elasticsearch operations.
This is the main entry point that composes connection, index, document,
and search operations into a unified client interface.

**Feature: observability-infrastructure**
**Requirement: R2 - Generic Elasticsearch Client**
**Refactored: 2025 - Split into modular components for maintainability**
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self

from infrastructure.elasticsearch.config import (
    ElasticsearchConnection,
)
from infrastructure.elasticsearch.index_operations import (
    DocumentOperations,
    IndexOperations,
)
from infrastructure.elasticsearch.search_operations import SearchOperations

if TYPE_CHECKING:
    from infrastructure.elasticsearch.config import (
        ElasticsearchClientConfig,
    )


class ElasticsearchClient:
    """Async Elasticsearch client wrapper.

    Provides connection management and common operations through
    composed operation classes.

    **Feature: observability-infrastructure**
    **Requirement: R2.2 - Client Wrapper**

    Example:
        >>> config = ElasticsearchClientConfig(hosts=["http://localhost:9200"])
        >>> async with ElasticsearchClient(config) as client:
        ...     health = await client.health()
        ...     print(health["status"])
    """

    def __init__(self, config: ElasticsearchClientConfig) -> None:
        """Initialize client with configuration.

        Args:
            config: Elasticsearch client configuration
        """
        self._connection = ElasticsearchConnection(config)
        self._index_ops = IndexOperations(self._connection._get_client)
        self._doc_ops = DocumentOperations(self._connection._get_client)
        self._search_ops = SearchOperations(self._connection._get_client)

    @property
    def client(self):
        """Get the raw Elasticsearch client."""
        return self._connection.client

    async def connect(self) -> Self:
        """Connect to Elasticsearch."""
        await self._connection.connect()
        return self

    async def close(self) -> None:
        """Close the connection."""
        await self._connection.close()

    async def __aenter__(self) -> Self:
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.close()

    # Health & Info (delegated to connection)

    async def health(self) -> dict[str, Any]:
        """Get cluster health."""
        return await self._connection.health()

    async def info(self) -> dict[str, Any]:
        """Get cluster info."""
        return await self._connection.info()

    async def ping(self) -> bool:
        """Ping the cluster."""
        return await self._connection.ping()

    # Index Management (delegated to index operations)

    async def create_index(
        self,
        index: str,
        mappings: dict[str, Any] | None = None,
        settings: dict[str, Any] | None = None,
    ) -> bool:
        """Create an index."""
        return await self._index_ops.create_index(index, mappings, settings)

    async def delete_index(self, index: str) -> bool:
        """Delete an index."""
        return await self._index_ops.delete_index(index)

    async def index_exists(self, index: str) -> bool:
        """Check if index exists."""
        return await self._index_ops.index_exists(index)

    async def refresh_index(self, index: str) -> None:
        """Refresh an index."""
        await self._index_ops.refresh_index(index)

    # Document Operations (delegated to document operations)

    async def index_document(
        self,
        index: str,
        document: dict[str, Any],
        doc_id: str | None = None,
        refresh: bool = False,
    ) -> dict[str, Any]:
        """Index a document."""
        return await self._doc_ops.index_document(index, document, doc_id, refresh)

    async def get_document(
        self,
        index: str,
        doc_id: str,
    ) -> dict[str, Any] | None:
        """Get a document by ID."""
        return await self._doc_ops.get_document(index, doc_id)

    async def update_document(
        self,
        index: str,
        doc_id: str,
        document: dict[str, Any],
        refresh: bool = False,
    ) -> dict[str, Any]:
        """Update a document."""
        return await self._doc_ops.update_document(index, doc_id, document, refresh)

    async def delete_document(
        self,
        index: str,
        doc_id: str,
        refresh: bool = False,
    ) -> bool:
        """Delete a document."""
        return await self._doc_ops.delete_document(index, doc_id, refresh)

    async def bulk(
        self,
        operations: list[dict[str, Any]],
        refresh: bool = False,
    ) -> dict[str, Any]:
        """Execute bulk operations."""
        return await self._doc_ops.bulk(operations, refresh)

    # Search Operations (delegated to search operations)

    async def search(
        self,
        index: str,
        query: dict[str, Any] | None = None,
        size: int = 10,
        from_: int = 0,
        sort: list[dict[str, Any]] | None = None,
        source: list[str] | bool | None = None,
        aggs: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Search documents."""
        return await self._search_ops.search(
            index, query, size, from_, sort, source, aggs
        )

    async def count(
        self,
        index: str,
        query: dict[str, Any] | None = None,
    ) -> int:
        """Count documents matching query."""
        return await self._search_ops.count(index, query)

    async def scroll(
        self,
        index: str,
        query: dict[str, Any] | None = None,
        size: int = 100,
        scroll: str = "5m",
    ):
        """Scroll through all documents matching query."""
        async for hit in self._search_ops.scroll(index, query, size, scroll):
            yield hit
