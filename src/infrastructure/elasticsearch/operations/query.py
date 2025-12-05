"""Elasticsearch query models.

**Feature: observability-infrastructure**
**Refactored: 2025 - Extracted from repository.py for SRP compliance**
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

from infrastructure.elasticsearch.document import ElasticsearchDocument

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
    ) -> AggregationResult:
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
