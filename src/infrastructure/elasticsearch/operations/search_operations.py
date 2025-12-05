"""Elasticsearch search operations.

**Feature: observability-infrastructure**
**Requirement: R2.4 - Search Operations**
"""

from __future__ import annotations

import contextlib
import logging
from typing import Any

logger = logging.getLogger(__name__)


class SearchOperations:
    """Handles Elasticsearch search, count, and scroll operations."""

    def __init__(self, client_getter: callable) -> None:
        """Initialize with client getter function.

        Args:
            client_getter: Async function that returns AsyncElasticsearch client
        """
        self._get_client = client_getter

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
            # Clear scroll - best effort cleanup
            if scroll_id:
                with contextlib.suppress(Exception):
                    await client.clear_scroll(scroll_id=scroll_id)
