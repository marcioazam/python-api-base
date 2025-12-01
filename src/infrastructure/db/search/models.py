"""Search models with PEP 695 generics.

**Feature: enterprise-features-2025, Task 7.1**
**Validates: Requirements 7.8, 7.9, 7.10**
"""

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class SearchQuery:
    """Search query parameters."""

    query: str
    filters: dict[str, Any] = field(default_factory=dict)
    sort: list[tuple[str, str]] = field(default_factory=list)
    page: int = 1
    page_size: int = 20
    highlight_fields: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class SearchResult[T]:
    """Generic search result with pagination.

    Type Parameters:
        T: The type of items in results.
    """

    items: tuple[T, ...]
    total: int
    page: int
    page_size: int
    facets: dict[str, dict[str, int]] = field(default_factory=dict)
    highlights: dict[str, list[str]] = field(default_factory=dict)

    @property
    def has_more(self) -> bool:
        """Check if there are more pages."""
        return self.page * self.page_size < self.total


class SearchProvider[TDocument](Protocol):
    """Protocol for search providers with PEP 695 generics."""

    async def index(self, doc_id: str, document: TDocument) -> None:
        """Index a document."""
        ...

    async def search(self, query: SearchQuery) -> SearchResult[TDocument]:
        """Search for documents."""
        ...

    async def delete(self, doc_id: str) -> bool:
        """Delete a document."""
        ...

    async def suggest(self, prefix: str, field: str) -> list[str]:
        """Get autocomplete suggestions."""
        ...


class Indexer[TEntity, TDocument](Protocol):
    """Protocol for entity-to-document mapping."""

    def to_document(self, entity: TEntity) -> TDocument:
        """Convert entity to searchable document."""
        ...

    def from_document(self, document: TDocument) -> TEntity:
        """Convert document back to entity."""
        ...
