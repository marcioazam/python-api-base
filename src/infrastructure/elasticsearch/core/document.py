"""Elasticsearch document base classes.

Provides base document types for Elasticsearch operations.

**Feature: observability-infrastructure**
**Requirement: R2 - Generic Elasticsearch Client**
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class DocumentMetadata(BaseModel):
    """Elasticsearch document metadata.

    Attributes:
        id: Document ID
        index: Index name
        version: Document version
        seq_no: Sequence number for optimistic concurrency
        primary_term: Primary term for optimistic concurrency
        score: Search relevance score (when from search)
    """

    id: str
    index: str
    version: int | None = None
    seq_no: int | None = None
    primary_term: int | None = None
    score: float | None = None


class ElasticsearchDocument(BaseModel):
    """Base class for Elasticsearch documents.

    All documents stored in Elasticsearch should inherit from this class.
    Provides common fields and serialization support.

    **Feature: observability-infrastructure**
    **Requirement: R2.1 - Document Base Class**

    Example:
        >>> class UserDocument(ElasticsearchDocument):
        ...     name: str
        ...     email: str
        >>> doc = UserDocument(name="John", email="john@example.com")
        >>> doc.to_dict()
        {'name': 'John', 'email': 'john@example.com', 'created_at': '...', 'updated_at': '...'}
    """

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Metadata (not stored in document, populated after operations)
    _metadata: DocumentMetadata | None = None

    model_config = {"extra": "allow"}

    @property
    def doc_id(self) -> str | None:
        """Get document ID from metadata."""
        return self._metadata.id if self._metadata else None

    def to_dict(self, exclude_none: bool = True) -> dict[str, Any]:
        """Convert document to dictionary for Elasticsearch.

        Args:
            exclude_none: Whether to exclude None values

        Returns:
            Dictionary representation of document
        """
        return self.model_dump(
            mode="json",
            exclude_none=exclude_none,
            exclude={"_metadata"},
        )

    @classmethod
    def from_hit(cls, hit: dict[str, Any]) -> ElasticsearchDocument:
        """Create document from Elasticsearch hit.

        Args:
            hit: Elasticsearch search hit

        Returns:
            Document instance with metadata
        """
        source = hit.get("_source", {})
        doc = cls.model_validate(source)

        doc._metadata = DocumentMetadata(
            id=hit.get("_id", ""),
            index=hit.get("_index", ""),
            version=hit.get("_version"),
            seq_no=hit.get("_seq_no"),
            primary_term=hit.get("_primary_term"),
            score=hit.get("_score"),
        )

        return doc

    def with_metadata(self, metadata: DocumentMetadata) -> ElasticsearchDocument:
        """Return a copy with updated metadata.

        Args:
            metadata: New metadata

        Returns:
            Document with updated metadata
        """
        self._metadata = metadata
        return self
