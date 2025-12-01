"""Search service implementation.

**Feature: enterprise-features-2025, Tasks 7.2-7.6**
**Validates: Requirements 7.1, 7.2, 7.4, 7.7**
"""

import logging

from .models import SearchQuery, SearchResult

logger = logging.getLogger(__name__)


class InMemorySearchProvider[TDocument]:
    """In-memory search provider for testing."""

    def __init__(self) -> None:
        self._documents: dict[str, TDocument] = {}

    async def index(self, doc_id: str, document: TDocument) -> None:
        """Index a document."""
        self._documents[doc_id] = document

    async def search(self, query: SearchQuery) -> SearchResult[TDocument]:
        """Search documents (simple substring match)."""
        results = []
        query_lower = query.query.lower()

        for doc_id, doc in self._documents.items():
            doc_str = str(doc).lower()
            if query_lower in doc_str:
                results.append(doc)

        # Apply pagination
        start = (query.page - 1) * query.page_size
        end = start + query.page_size
        page_results = results[start:end]

        return SearchResult(
            items=tuple(page_results),
            total=len(results),
            page=query.page,
            page_size=query.page_size,
        )

    async def delete(self, doc_id: str) -> bool:
        """Delete a document."""
        if doc_id in self._documents:
            del self._documents[doc_id]
            return True
        return False

    async def suggest(self, prefix: str, field: str) -> list[str]:
        """Get suggestions (returns empty for in-memory)."""
        return []

    async def bulk_index(self, documents: dict[str, TDocument]) -> int:
        """Bulk index documents."""
        for doc_id, doc in documents.items():
            self._documents[doc_id] = doc
        return len(documents)


class SearchService[TDocument]:
    """Service for managing search operations."""

    def __init__(
        self,
        provider: InMemorySearchProvider[TDocument],
        fallback_enabled: bool = True,
    ) -> None:
        self._provider = provider
        self._fallback_enabled = fallback_enabled

    async def index(self, doc_id: str, document: TDocument) -> None:
        """Index a document."""
        await self._provider.index(doc_id, document)

    async def search(self, query: SearchQuery) -> SearchResult[TDocument]:
        """Search for documents."""
        return await self._provider.search(query)

    async def delete(self, doc_id: str) -> bool:
        """Delete a document."""
        return await self._provider.delete(doc_id)

    async def suggest(self, prefix: str, field: str) -> list[str]:
        """Get autocomplete suggestions."""
        return await self._provider.suggest(prefix, field)

    async def reindex_all(self, documents: dict[str, TDocument]) -> int:
        """Reindex all documents."""
        return await self._provider.bulk_index(documents)
