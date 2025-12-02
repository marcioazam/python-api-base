"""Generic Elasticsearch client with PEP 695 generics.

Provides a type-safe async client for Elasticsearch operations.

**Feature: observability-infrastructure**
**Requirement: R2 - Generic Elasticsearch Client**
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Self

if TYPE_CHECKING:
    from elasticsearch import AsyncElasticsearch

logger = logging.getLogger(__name__)


@dataclass
class ElasticsearchClientConfig:
    """Configuration for Elasticsearch client.

    Attributes:
        hosts: List of Elasticsearch hosts
        username: Optional username for authentication
        password: Optional password for authentication
        api_key: Optional API key for authentication
        use_ssl: Whether to use SSL/TLS
        verify_certs: Whether to verify SSL certificates
        ca_certs: Path to CA certificates
        timeout: Connection timeout in seconds
        max_retries: Maximum retry attempts
        retry_on_timeout: Whether to retry on timeout
    """

    hosts: list[str] = field(default_factory=lambda: ["http://localhost:9200"])
    username: str | None = None
    password: str | None = None
    api_key: str | tuple[str, str] | None = None
    use_ssl: bool = False
    verify_certs: bool = True
    ca_certs: str | None = None
    timeout: int = 30
    max_retries: int = 3
    retry_on_timeout: bool = True


class ElasticsearchClient:
    """Async Elasticsearch client wrapper.

    Provides connection management and common operations.

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
        self._config = config
        self._client: AsyncElasticsearch | None = None

    async def _get_client(self) -> AsyncElasticsearch:
        """Get or create the Elasticsearch client."""
        if self._client is None:
            from elasticsearch import AsyncElasticsearch

            # Build auth params
            auth_params: dict[str, Any] = {}
            if self._config.api_key:
                auth_params["api_key"] = self._config.api_key
            elif self._config.username and self._config.password:
                auth_params["basic_auth"] = (
                    self._config.username,
                    self._config.password,
                )

            # Build SSL params
            ssl_params: dict[str, Any] = {}
            if self._config.use_ssl:
                ssl_params["use_ssl"] = True
                ssl_params["verify_certs"] = self._config.verify_certs
                if self._config.ca_certs:
                    ssl_params["ca_certs"] = self._config.ca_certs

            self._client = AsyncElasticsearch(
                hosts=self._config.hosts,
                timeout=self._config.timeout,
                max_retries=self._config.max_retries,
                retry_on_timeout=self._config.retry_on_timeout,
                **auth_params,
                **ssl_params,
            )

        return self._client

    @property
    def client(self) -> AsyncElasticsearch:
        """Get the raw Elasticsearch client.

        Raises:
            RuntimeError: If client is not connected
        """
        if self._client is None:
            raise RuntimeError(
                "Client not connected. Use 'async with' or call connect()"
            )
        return self._client

    async def connect(self) -> Self:
        """Connect to Elasticsearch.

        Returns:
            Self for chaining
        """
        await self._get_client()
        logger.info("Connected to Elasticsearch", extra={"hosts": self._config.hosts})
        return self

    async def close(self) -> None:
        """Close the connection."""
        if self._client:
            await self._client.close()
            self._client = None
            logger.info("Disconnected from Elasticsearch")

    async def __aenter__(self) -> Self:
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.close()

    # Health & Info

    async def health(self) -> dict[str, Any]:
        """Get cluster health.

        Returns:
            Cluster health information
        """
        client = await self._get_client()
        return await client.cluster.health()

    async def info(self) -> dict[str, Any]:
        """Get cluster info.

        Returns:
            Cluster information
        """
        client = await self._get_client()
        return await client.info()

    async def ping(self) -> bool:
        """Ping the cluster.

        Returns:
            True if cluster is reachable
        """
        client = await self._get_client()
        return await client.ping()

    # Index Management

    async def create_index(
        self,
        index: str,
        mappings: dict[str, Any] | None = None,
        settings: dict[str, Any] | None = None,
    ) -> bool:
        """Create an index.

        Args:
            index: Index name
            mappings: Index mappings
            settings: Index settings

        Returns:
            True if created successfully
        """
        client = await self._get_client()

        body: dict[str, Any] = {}
        if mappings:
            body["mappings"] = mappings
        if settings:
            body["settings"] = settings

        try:
            await client.indices.create(index=index, body=body if body else None)
            logger.info(f"Created index: {index}")
            return True
        except Exception as e:
            logger.error(f"Failed to create index {index}: {e}")
            raise

    async def delete_index(self, index: str) -> bool:
        """Delete an index.

        Args:
            index: Index name

        Returns:
            True if deleted successfully
        """
        client = await self._get_client()

        try:
            await client.indices.delete(index=index)
            logger.info(f"Deleted index: {index}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete index {index}: {e}")
            raise

    async def index_exists(self, index: str) -> bool:
        """Check if index exists.

        Args:
            index: Index name

        Returns:
            True if index exists
        """
        client = await self._get_client()
        return await client.indices.exists(index=index)

    async def refresh_index(self, index: str) -> None:
        """Refresh an index (make recent changes searchable).

        Args:
            index: Index name
        """
        client = await self._get_client()
        await client.indices.refresh(index=index)

    # Document Operations

    async def index_document(
        self,
        index: str,
        document: dict[str, Any],
        doc_id: str | None = None,
        refresh: bool = False,
    ) -> dict[str, Any]:
        """Index a document.

        Args:
            index: Index name
            document: Document to index
            doc_id: Optional document ID
            refresh: Whether to refresh after indexing

        Returns:
            Index response with _id, _version, etc.
        """
        client = await self._get_client()

        result = await client.index(
            index=index,
            id=doc_id,
            document=document,
            refresh=refresh,
        )

        return dict(result)

    async def get_document(
        self,
        index: str,
        doc_id: str,
    ) -> dict[str, Any] | None:
        """Get a document by ID.

        Args:
            index: Index name
            doc_id: Document ID

        Returns:
            Document or None if not found
        """
        client = await self._get_client()

        try:
            result = await client.get(index=index, id=doc_id)
            return dict(result)
        except Exception:
            return None

    async def update_document(
        self,
        index: str,
        doc_id: str,
        document: dict[str, Any],
        refresh: bool = False,
    ) -> dict[str, Any]:
        """Update a document.

        Args:
            index: Index name
            doc_id: Document ID
            document: Partial document with fields to update
            refresh: Whether to refresh after update

        Returns:
            Update response
        """
        client = await self._get_client()

        result = await client.update(
            index=index,
            id=doc_id,
            doc=document,
            refresh=refresh,
        )

        return dict(result)

    async def delete_document(
        self,
        index: str,
        doc_id: str,
        refresh: bool = False,
    ) -> bool:
        """Delete a document.

        Args:
            index: Index name
            doc_id: Document ID
            refresh: Whether to refresh after delete

        Returns:
            True if deleted
        """
        client = await self._get_client()

        try:
            await client.delete(index=index, id=doc_id, refresh=refresh)
            return True
        except Exception:
            return False

    async def bulk(
        self,
        operations: list[dict[str, Any]],
        refresh: bool = False,
    ) -> dict[str, Any]:
        """Execute bulk operations.

        Args:
            operations: List of bulk operations
            refresh: Whether to refresh after bulk

        Returns:
            Bulk response
        """
        client = await self._get_client()

        result = await client.bulk(operations=operations, refresh=refresh)
        return dict(result)

    # Search Operations

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
        """Search documents.

        Args:
            index: Index name or pattern
            query: Elasticsearch query DSL
            size: Number of results to return
            from_: Offset for pagination
            sort: Sort specification
            source: Fields to include in response
            aggs: Aggregations

        Returns:
            Search response
        """
        client = await self._get_client()

        body: dict[str, Any] = {
            "size": size,
            "from": from_,
        }

        if query:
            body["query"] = query
        if sort:
            body["sort"] = sort
        if source is not None:
            body["_source"] = source
        if aggs:
            body["aggs"] = aggs

        result = await client.search(index=index, body=body)
        return dict(result)

    async def count(
        self,
        index: str,
        query: dict[str, Any] | None = None,
    ) -> int:
        """Count documents matching query.

        Args:
            index: Index name or pattern
            query: Elasticsearch query DSL

        Returns:
            Document count
        """
        client = await self._get_client()

        body = {"query": query} if query else None
        result = await client.count(index=index, body=body)

        return result["count"]

    async def scroll(
        self,
        index: str,
        query: dict[str, Any] | None = None,
        size: int = 100,
        scroll: str = "5m",
    ):
        """Scroll through all documents matching query.

        Args:
            index: Index name or pattern
            query: Elasticsearch query DSL
            size: Batch size
            scroll: Scroll timeout

        Yields:
            Document hits
        """
        client = await self._get_client()

        body: dict[str, Any] = {"size": size}
        if query:
            body["query"] = query

        # Initial search
        result = await client.search(index=index, body=body, scroll=scroll)
        scroll_id = result.get("_scroll_id")

        try:
            while True:
                hits = result["hits"]["hits"]
                if not hits:
                    break

                for hit in hits:
                    yield hit

                # Get next batch
                result = await client.scroll(scroll_id=scroll_id, scroll=scroll)
                scroll_id = result.get("_scroll_id")

        finally:
            # Clear scroll
            if scroll_id:
                try:
                    await client.clear_scroll(scroll_id=scroll_id)
                except Exception:
                    pass
