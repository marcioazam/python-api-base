"""Unit tests for Elasticsearch repository.

**Feature: observability-infrastructure**
**Requirement: R2 - Generic Elasticsearch Client**
"""

import pytest

from infrastructure.elasticsearch.repository import (
    SearchQuery,
    SearchResult,
    AggregationResult,
)
from infrastructure.elasticsearch.document import ElasticsearchDocument


class SampleDocument(ElasticsearchDocument):
    """Sample document for testing."""

    name: str
    email: str


class TestSearchQuery:
    """Tests for SearchQuery."""

    def test_build_empty_query(self) -> None:
        """Test building empty query."""
        query = SearchQuery()
        body = query.build()

        assert body["size"] == 10
        assert body["from"] == 0
        assert "query" not in body

    def test_build_with_query(self) -> None:
        """Test building with query."""
        query = SearchQuery(
            query={"match": {"name": "John"}},
            size=20,
            from_=10,
        )
        body = query.build()

        assert body["size"] == 20
        assert body["from"] == 10
        assert "query" in body
        assert body["query"]["bool"]["must"][0]["match"]["name"] == "John"

    def test_build_with_filters(self) -> None:
        """Test building with filters."""
        query = SearchQuery(
            filters=[
                {"term": {"status": "active"}},
                {"range": {"age": {"gte": 18}}},
            ]
        )
        body = query.build()

        assert "query" in body
        assert "filter" in body["query"]["bool"]
        assert len(body["query"]["bool"]["filter"]) == 2

    def test_build_with_sort(self) -> None:
        """Test building with sort."""
        query = SearchQuery(
            sort=[{"created_at": {"order": "desc"}}]
        )
        body = query.build()

        assert "sort" in body
        assert body["sort"][0]["created_at"]["order"] == "desc"

    def test_build_with_source(self) -> None:
        """Test building with source filter."""
        query = SearchQuery(
            source=["name", "email"]
        )
        body = query.build()

        assert body["_source"] == ["name", "email"]

    def test_build_with_aggs(self) -> None:
        """Test building with aggregations."""
        query = SearchQuery(
            aggs={
                "status_count": {
                    "terms": {"field": "status"}
                }
            }
        )
        body = query.build()

        assert "aggs" in body
        assert "status_count" in body["aggs"]

    def test_build_with_highlight(self) -> None:
        """Test building with highlight."""
        query = SearchQuery(
            highlight={
                "fields": {"content": {}}
            }
        )
        body = query.build()

        assert "highlight" in body


class TestSearchResult:
    """Tests for SearchResult."""

    def test_empty_result(self) -> None:
        """Test empty search result."""
        result = SearchResult[SampleDocument](
            hits=[],
            total=0,
        )

        assert result.is_empty
        assert len(result) == 0
        assert result.total == 0

    def test_result_with_hits(self) -> None:
        """Test result with hits."""
        docs = [
            SampleDocument(name="John", email="john@example.com"),
            SampleDocument(name="Jane", email="jane@example.com"),
        ]

        result = SearchResult[SampleDocument](
            hits=docs,
            total=2,
            max_score=1.5,
            took_ms=10,
        )

        assert not result.is_empty
        assert len(result) == 2
        assert result.total == 2
        assert result.max_score == 1.5
        assert result.took_ms == 10

    def test_result_iteration(self) -> None:
        """Test iterating over result."""
        docs = [
            SampleDocument(name="John", email="john@example.com"),
            SampleDocument(name="Jane", email="jane@example.com"),
        ]

        result = SearchResult[SampleDocument](hits=docs, total=2)

        names = [doc.name for doc in result]
        assert names == ["John", "Jane"]


class TestAggregationResult:
    """Tests for AggregationResult."""

    def test_bucket_aggregation(self) -> None:
        """Test bucket aggregation result."""
        agg_response = {
            "buckets": [
                {"key": "active", "doc_count": 100},
                {"key": "inactive", "doc_count": 50},
            ]
        }

        result = AggregationResult.from_response("status", agg_response)

        assert result.name == "status"
        assert len(result.buckets) == 2
        assert result.buckets[0]["key"] == "active"
        assert result.buckets[0]["doc_count"] == 100

    def test_metric_aggregation(self) -> None:
        """Test metric aggregation result."""
        agg_response = {
            "value": 42.5
        }

        result = AggregationResult.from_response("avg_age", agg_response)

        assert result.name == "avg_age"
        assert result.value == 42.5
        assert len(result.buckets) == 0

    def test_raw_response_preserved(self) -> None:
        """Test that raw response is preserved."""
        agg_response = {
            "buckets": [],
            "doc_count_error_upper_bound": 0,
            "sum_other_doc_count": 10,
        }

        result = AggregationResult.from_response("terms", agg_response)

        assert result.raw == agg_response
