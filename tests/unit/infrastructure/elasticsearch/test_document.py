"""Unit tests for Elasticsearch document classes.

**Feature: observability-infrastructure**
**Requirement: R2 - Generic Elasticsearch Client**
"""

import pytest
from datetime import datetime, UTC

from infrastructure.elasticsearch.document import (
    ElasticsearchDocument,
    DocumentMetadata,
)


class SampleDocument(ElasticsearchDocument):
    """Sample document for testing."""

    name: str
    email: str
    age: int | None = None


class TestDocumentMetadata:
    """Tests for DocumentMetadata."""

    def test_create_metadata(self) -> None:
        """Test creating metadata."""
        metadata = DocumentMetadata(
            id="doc-123",
            index="test-index",
            version=1,
            seq_no=5,
            primary_term=1,
        )

        assert metadata.id == "doc-123"
        assert metadata.index == "test-index"
        assert metadata.version == 1

    def test_metadata_with_score(self) -> None:
        """Test metadata with search score."""
        metadata = DocumentMetadata(
            id="doc-123",
            index="test-index",
            score=1.5,
        )

        assert metadata.score == 1.5


class TestElasticsearchDocument:
    """Tests for ElasticsearchDocument."""

    def test_create_document(self) -> None:
        """Test creating a document."""
        doc = SampleDocument(name="John", email="john@example.com")

        assert doc.name == "John"
        assert doc.email == "john@example.com"
        assert doc.created_at is not None
        assert doc.updated_at is not None

    def test_to_dict(self) -> None:
        """Test converting document to dict."""
        doc = SampleDocument(name="John", email="john@example.com", age=30)
        data = doc.to_dict()

        assert data["name"] == "John"
        assert data["email"] == "john@example.com"
        assert data["age"] == 30
        assert "created_at" in data
        assert "updated_at" in data

    def test_to_dict_exclude_none(self) -> None:
        """Test that None values are excluded by default."""
        doc = SampleDocument(name="John", email="john@example.com")
        data = doc.to_dict()

        assert "age" not in data  # age is None, should be excluded

    def test_to_dict_include_none(self) -> None:
        """Test including None values."""
        doc = SampleDocument(name="John", email="john@example.com")
        data = doc.to_dict(exclude_none=False)

        assert "age" in data
        assert data["age"] is None

    def test_from_hit(self) -> None:
        """Test creating document from ES hit."""
        hit = {
            "_id": "doc-123",
            "_index": "test-index",
            "_version": 1,
            "_seq_no": 5,
            "_primary_term": 1,
            "_score": 1.5,
            "_source": {
                "name": "John",
                "email": "john@example.com",
                "age": 30,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            },
        }

        doc = SampleDocument.from_hit(hit)

        assert doc.name == "John"
        assert doc.email == "john@example.com"
        assert doc.age == 30
        assert doc._metadata is not None
        assert doc._metadata.id == "doc-123"
        assert doc._metadata.index == "test-index"
        assert doc._metadata.score == 1.5

    def test_doc_id_property(self) -> None:
        """Test doc_id property."""
        doc = SampleDocument(name="John", email="john@example.com")

        # Without metadata
        assert doc.doc_id is None

        # With metadata
        metadata = DocumentMetadata(id="doc-123", index="test")
        doc._metadata = metadata
        assert doc.doc_id == "doc-123"

    def test_with_metadata(self) -> None:
        """Test with_metadata method."""
        doc = SampleDocument(name="John", email="john@example.com")
        metadata = DocumentMetadata(id="doc-456", index="test-index")

        result = doc.with_metadata(metadata)

        assert result._metadata is not None
        assert result._metadata.id == "doc-456"
        assert result is doc  # Same instance

    def test_extra_fields_allowed(self) -> None:
        """Test that extra fields are allowed."""
        doc = SampleDocument(
            name="John",
            email="john@example.com",
            custom_field="custom_value",
        )

        data = doc.to_dict()
        assert data.get("custom_field") == "custom_value"
