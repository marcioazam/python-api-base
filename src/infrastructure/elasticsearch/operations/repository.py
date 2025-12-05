"""Generic Elasticsearch repository with PEP 695 generics.

Provides type-safe CRUD and search operations for Elasticsearch documents.

**Feature: observability-infrastructure**
**Requirement: R2 - Generic Elasticsearch Client**
**Refactored: 2025 - Split 476 lines into focused modules**
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from infrastructure.elasticsearch.document import (
    DocumentMetadata,
    ElasticsearchDocument,
)
from infrastructure.elasticsearch.query import (
    AggregationResult,
    SearchQuery,
    SearchResult,
)

if TYPE_CHECKING:
    from infrastructure.elasticsearch.client import ElasticsearchClient

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=ElasticsearchDocument)


class ElasticsearchRepository(Generic[T]):
    """Generic repository for Elasticsearch documents.

    Provides type-safe CRUD and search operations using PEP 695 generics pattern.

    **Feature: observability-infrastructure**
    **Requirement: R2.3 - Generic Repository**

    Example:
        >>> class UserDocument(ElasticsearchDocument):
        ...     name: str
        ...     email: str
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
        """Create a new document."""
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
        """Get document by ID."""
        result = await self._client.get_document(index=self._index, doc_id=doc_id)

        if not result:
            return None

        return self._document_class.from_hit(result)

    async def update(
        self,
        doc_id: str,
        document: T | dict[str, Any],
        refresh: bool = False,
    ) -> T | None:
        """Update a document."""
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

        return await self.get(doc_id)

    async def delete(self, doc_id: str, refresh: bool = False) -> bool:
        """Delete a document."""
        return await self._client.delete_document(
            index=self._index,
            doc_id=doc_id,
            refresh=refresh,
        )

    async def exists(self, doc_id: str) -> bool:
        """Check if document exists."""
        result = await self._client.get_document(index=self._index, doc_id=doc_id)
        return result is not None

    # Bulk Operations

    async def bulk_create(
        self,
        documents: list[T],
        refresh: bool = False,
    ) -> list[T]:
        """Bulk create documents."""
        operations: list[dict[str, Any]] = []

        for doc in documents:
            doc.updated_at = datetime.now(UTC)
            operations.append({"index": {"_index": self._index}})
            operations.append(doc.to_dict())

        result = await self._client.bulk(operations=operations, refresh=refresh)

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
        """Bulk delete documents."""
        operations: list[dict[str, Any]] = [
            {"delete": {"_index": self._index, "_id": doc_id}} for doc_id in doc_ids
        ]

        result = await self._client.bulk(operations=operations, refresh=refresh)

        return sum(
            1
            for item in result.get("items", [])
            if "delete" in item and item["delete"].get("result") == "deleted"
        )

    # Search Operations

    async def search(self, query: SearchQuery) -> SearchResult[T]:
        """Search documents."""
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

        hits = [self._document_class.from_hit(hit) for hit in result["hits"]["hits"]]

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
        """Find all documents."""
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
        """Find documents by field value."""
        query = SearchQuery(query={"term": {field: value}}, size=size)
        return await self.search(query)

    async def find_by_text(
        self,
        text: str,
        fields: list[str] | None = None,
        size: int = 10,
    ) -> SearchResult[T]:
        """Full-text search across fields."""
        if fields:
            es_query = {"multi_match": {"query": text, "fields": fields}}
        else:
            es_query = {"query_string": {"query": text}}

        query = SearchQuery(query=es_query, size=size)
        return await self.search(query)

    async def count(self, query: dict[str, Any] | None = None) -> int:
        """Count documents matching query."""
        return await self._client.count(index=self._index, query=query)

    async def aggregate(
        self,
        aggs: dict[str, Any],
        query: dict[str, Any] | None = None,
    ) -> dict[str, AggregationResult]:
        """Execute aggregations."""
        result = await self._client.search(
            index=self._index,
            query=query,
            size=0,
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
        """Scroll through all matching documents."""
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
        """Ensure index exists, create if not."""
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


# Re-export query models for backward compatibility
__all__ = [
    "AggregationResult",
    "ElasticsearchRepository",
    "SearchQuery",
    "SearchResult",
]
