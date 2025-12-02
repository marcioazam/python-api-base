"""Generic Elasticsearch repository with PEP 695 generics.

Provides type-safe CRUD and search operations for Elasticsearch documents.

**Feature: observability-infrastructure**
**Requirement: R2 - Generic Elasticsearch Client**
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

from infrastructure.elasticsearch.client import ElasticsearchClient
from infrastructure.elasticsearch.document import (
    DocumentMetadata,
    ElasticsearchDocument,
)

logger = logging.getLogger(__name__)

# PEP 695 style would be: class ElasticsearchRepository[T: ElasticsearchDocument]
# Using TypeVar for compatibility
T = TypeVar("T", bound=ElasticsearchDocument)


@dataclass
class SearchQuery:
    """Search query specification.

    Attributes:
        query: Elasticsearch query DSL
        filters: Additional filters to apply
        size: Number of results
        from_: Pagination offset
        sort: Sort specification
        source: Fields to include
        aggs: Aggregations
        highlight: Highlight configuration
    """

    query: dict[str, Any] | None = None
    filters: list[dict[str, Any]] = field(default_factory=list)
    size: int = 10
    from_: int = 0
    sort: list[dict[str, Any]] = field(default_factory=list)
    source: list[str] | None = None
    aggs: dict[str, Any] | None = None
    highlight: dict[str, Any] | None = None

    def build(self) -> dict[str, Any]:
        """Build Elasticsearch query body.

        Returns:
            Query body dict
        """
        body: dict[str, Any] = {
            "size": self.size,
            "from": self.from_,
        }

        # Build bool query with filters
        if self.query or self.filters:
            bool_query: dict[str, Any] = {}

            if self.query:
                bool_query["must"] = [self.query]

            if self.filters:
                bool_query["filter"] = self.filters

            body["query"] = {"bool": bool_query}

        if self.sort:
            body["sort"] = self.sort

        if self.source:
            body["_source"] = self.source

        if self.aggs:
            body["aggs"] = self.aggs

        if self.highlight:
            body["highlight"] = self.highlight

        return body


@dataclass
class SearchResult(Generic[T]):
    """Search result container.

    Attributes:
        hits: List of matching documents
        total: Total number of matches
        max_score: Maximum relevance score
        aggregations: Aggregation results
        took_ms: Query execution time in milliseconds
    """

    hits: list[T]
    total: int
    max_score: float | None = None
    aggregations: dict[str, Any] | None = None
    took_ms: int = 0

    @property
    def is_empty(self) -> bool:
        """Check if result is empty."""
        return len(self.hits) == 0

    def __iter__(self):
        """Iterate over hits."""
        return iter(self.hits)

    def __len__(self) -> int:
        """Return number of hits."""
        return len(self.hits)


@dataclass
class AggregationResult:
    """Aggregation result wrapper.

    Attributes:
        name: Aggregation name
        buckets: Bucket aggregation results
        value: Metric aggregation value
        raw: Raw aggregation response
    """

    name: str
    buckets: list[dict[str, Any]] = field(default_factory=list)
    value: float | int | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_response(
        cls,
        name: str,
        agg_response: dict[str, Any],
    ) -> "AggregationResult":
        """Create from Elasticsearch aggregation response.

        Args:
            name: Aggregation name
            agg_response: Raw aggregation response

        Returns:
            AggregationResult instance
        """
        buckets = agg_response.get("buckets", [])
        value = agg_response.get("value")

        return cls(
            name=name,
            buckets=buckets,
            value=value,
            raw=agg_response,
        )


class ElasticsearchRepository(Generic[T]):
    """Generic repository for Elasticsearch documents.

    Provides type-safe CRUD and search operations using PEP 695 generics pattern.

    **Feature: observability-infrastructure**
    **Requirement: R2.3 - Generic Repository**

    Example:
        >>> class UserDocument(ElasticsearchDocument):
        ...     name: str
        ...     email: str
        ...
        >>> repo = ElasticsearchRepository[UserDocument](
        ...     client=client,
        ...     index="users",
        ...     document_class=UserDocument,
        ... )
        >>> user = await repo.create(UserDocument(name="John", email="john@example.com"))
        >>> found = await repo.get(user.doc_id)
    """

    def __init__(
        self,
        client: ElasticsearchClient,
        index: str,
        document_class: type[T],
    ) -> None:
        """Initialize repository.

        Args:
            client: Elasticsearch client
            index: Default index name
            document_class: Document class for type conversion
        """
        self._client = client
        self._index = index
        self._document_class = document_class

    @property
    def index(self) -> str:
        """Get index name."""
        return self._index

    # CRUD Operations

    async def create(
        self,
        document: T,
        doc_id: str | None = None,
        refresh: bool = False,
    ) -> T:
        """Create a new document.

        Args:
            document: Document to create
            doc_id: Optional document ID (auto-generated if not provided)
            refresh: Whether to refresh index after create

        Returns:
            Created document with metadata
        """
        document.updated_at = datetime.now(UTC)

        result = await self._client.index_document(
            index=self._index,
            document=document.to_dict(),
            doc_id=doc_id,
            refresh=refresh,
        )

        metadata = DocumentMetadata(
            id=result["_id"],
            index=result["_index"],
            version=result.get("_version"),
            seq_no=result.get("_seq_no"),
            primary_term=result.get("_primary_term"),
        )

        return document.with_metadata(metadata)

    async def get(self, doc_id: str) -> T | None:
        """Get document by ID.

        Args:
            doc_id: Document ID

        Returns:
            Document or None if not found
        """
        result = await self._client.get_document(
            index=self._index,
            doc_id=doc_id,
        )

        if not result:
            return None

        return self._document_class.from_hit(result)

    async def update(
        self,
        doc_id: str,
        document: T | dict[str, Any],
        refresh: bool = False,
    ) -> T | None:
        """Update a document.

        Args:
            doc_id: Document ID
            document: Full document or partial update dict
            refresh: Whether to refresh after update

        Returns:
            Updated document or None if not found
        """
        if isinstance(document, ElasticsearchDocument):
            document.updated_at = datetime.now(UTC)
            update_data = document.to_dict()
        else:
            update_data = document
            update_data["updated_at"] = datetime.now(UTC).isoformat()

        await self._client.update_document(
            index=self._index,
            doc_id=doc_id,
            document=update_data,
            refresh=refresh,
        )

        # Fetch updated document
        return await self.get(doc_id)

    async def delete(self, doc_id: str, refresh: bool = False) -> bool:
        """Delete a document.

        Args:
            doc_id: Document ID
            refresh: Whether to refresh after delete

        Returns:
            True if deleted, False if not found
        """
        return await self._client.delete_document(
            index=self._index,
            doc_id=doc_id,
            refresh=refresh,
        )

    async def exists(self, doc_id: str) -> bool:
        """Check if document exists.

        Args:
            doc_id: Document ID

        Returns:
            True if document exists
        """
        result = await self._client.get_document(
            index=self._index,
            doc_id=doc_id,
        )
        return result is not None

    # Bulk Operations

    async def bulk_create(
        self,
        documents: list[T],
        refresh: bool = False,
    ) -> list[T]:
        """Bulk create documents.

        Args:
            documents: Documents to create
            refresh: Whether to refresh after bulk

        Returns:
            Created documents with metadata
        """
        operations: list[dict[str, Any]] = []

        for doc in documents:
            doc.updated_at = datetime.now(UTC)
            operations.append({"index": {"_index": self._index}})
            operations.append(doc.to_dict())

        result = await self._client.bulk(operations=operations, refresh=refresh)

        # Update documents with metadata from response
        for i, item in enumerate(result.get("items", [])):
            if "index" in item:
                index_result = item["index"]
                metadata = DocumentMetadata(
                    id=index_result["_id"],
                    index=index_result["_index"],
                    version=index_result.get("_version"),
                    seq_no=index_result.get("_seq_no"),
                    primary_term=index_result.get("_primary_term"),
                )
                documents[i] = documents[i].with_metadata(metadata)

        return documents

    async def bulk_delete(
        self,
        doc_ids: list[str],
        refresh: bool = False,
    ) -> int:
        """Bulk delete documents.

        Args:
            doc_ids: Document IDs to delete
            refresh: Whether to refresh after bulk

        Returns:
            Number of documents deleted
        """
        operations: list[dict[str, Any]] = []

        for doc_id in doc_ids:
            operations.append({"delete": {"_index": self._index, "_id": doc_id}})

        result = await self._client.bulk(operations=operations, refresh=refresh)

        # Count successful deletes
        deleted = sum(
            1 for item in result.get("items", [])
            if "delete" in item and item["delete"].get("result") == "deleted"
        )

        return deleted

    # Search Operations

    async def search(self, query: SearchQuery) -> SearchResult[T]:
        """Search documents.

        Args:
            query: Search query specification

        Returns:
            Search result with typed documents
        """
        body = query.build()

        result = await self._client.search(
            index=self._index,
            query=body.get("query"),
            size=body.get("size", 10),
            from_=body.get("from", 0),
            sort=body.get("sort"),
            source=body.get("_source"),
            aggs=body.get("aggs"),
        )

        hits = [
            self._document_class.from_hit(hit)
            for hit in result["hits"]["hits"]
        ]

        total_hits = result["hits"]["total"]
        total = total_hits["value"] if isinstance(total_hits, dict) else total_hits

        return SearchResult(
            hits=hits,
            total=total,
            max_score=result["hits"].get("max_score"),
            aggregations=result.get("aggregations"),
            took_ms=result.get("took", 0),
        )

    async def find_all(
        self,
        size: int = 100,
        sort: list[dict[str, Any]] | None = None,
    ) -> SearchResult[T]:
        """Find all documents.

        Args:
            size: Maximum number to return
            sort: Sort specification

        Returns:
            Search result with all documents
        """
        query = SearchQuery(
            query={"match_all": {}},
            size=size,
            sort=sort or [{"created_at": {"order": "desc"}}],
        )
        return await self.search(query)

    async def find_by_field(
        self,
        field: str,
        value: Any,
        size: int = 10,
    ) -> SearchResult[T]:
        """Find documents by field value.

        Args:
            field: Field name
            value: Field value
            size: Maximum number to return

        Returns:
            Search result
        """
        query = SearchQuery(
            query={"term": {field: value}},
            size=size,
        )
        return await self.search(query)

    async def find_by_text(
        self,
        text: str,
        fields: list[str] | None = None,
        size: int = 10,
    ) -> SearchResult[T]:
        """Full-text search across fields.

        Args:
            text: Search text
            fields: Fields to search (defaults to all)
            size: Maximum number to return

        Returns:
            Search result
        """
        if fields:
            es_query = {"multi_match": {"query": text, "fields": fields}}
        else:
            es_query = {"query_string": {"query": text}}

        query = SearchQuery(query=es_query, size=size)
        return await self.search(query)

    async def count(self, query: dict[str, Any] | None = None) -> int:
        """Count documents matching query.

        Args:
            query: Optional query filter

        Returns:
            Document count
        """
        return await self._client.count(index=self._index, query=query)

    async def aggregate(
        self,
        aggs: dict[str, Any],
        query: dict[str, Any] | None = None,
    ) -> dict[str, AggregationResult]:
        """Execute aggregations.

        Args:
            aggs: Aggregation specification
            query: Optional query filter

        Returns:
            Dict of aggregation results by name
        """
        result = await self._client.search(
            index=self._index,
            query=query,
            size=0,  # Don't need hits for aggregations
            aggs=aggs,
        )

        aggregations = result.get("aggregations", {})

        return {
            name: AggregationResult.from_response(name, agg_data)
            for name, agg_data in aggregations.items()
        }

    # Iteration

    async def scroll_all(
        self,
        query: dict[str, Any] | None = None,
        batch_size: int = 100,
    ):
        """Scroll through all matching documents.

        Args:
            query: Optional query filter
            batch_size: Number of documents per batch

        Yields:
            Documents one at a time
        """
        async for hit in self._client.scroll(
            index=self._index,
            query=query,
            size=batch_size,
        ):
            yield self._document_class.from_hit(hit)

    # Index Management

    async def ensure_index(
        self,
        mappings: dict[str, Any] | None = None,
        settings: dict[str, Any] | None = None,
    ) -> bool:
        """Ensure index exists, create if not.

        Args:
            mappings: Index mappings
            settings: Index settings

        Returns:
            True if created, False if already existed
        """
        if await self._client.index_exists(self._index):
            return False

        await self._client.create_index(
            index=self._index,
            mappings=mappings,
            settings=settings,
        )
        return True

    async def refresh(self) -> None:
        """Refresh the index."""
        await self._client.refresh_index(self._index)
