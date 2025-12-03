"""Elasticsearch log buffer and fallback handling.

**Feature: observability-infrastructure**
**Requirement: R1.3 - Ship logs to Elasticsearch with buffering**
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from elasticsearch import AsyncElasticsearch


class LogBuffer:
    """Buffered log storage with periodic flushing.

    **Feature: observability-infrastructure**
    **Requirement: R1.3 - Batched bulk indexing**
    """

    def __init__(
        self,
        batch_size: int = 100,
        flush_interval_seconds: float = 5.0,
    ) -> None:
        """Initialize log buffer.

        Args:
            batch_size: Number of logs to batch before auto-flush
            flush_interval_seconds: Max seconds between flushes
        """
        self._batch_size = batch_size
        self._flush_interval = flush_interval_seconds
        self._buffer: list[dict[str, Any]] = []
        self._flush_task: asyncio.Task[None] | None = None
        self._closed = False

    def add(self, event: dict[str, Any]) -> bool:
        """Add event to buffer.

        Args:
            event: Log event to buffer

        Returns:
            True if buffer should be flushed
        """
        if self._closed:
            return False

        self._buffer.append(event)
        return len(self._buffer) >= self._batch_size

    def take_all(self) -> list[dict[str, Any]]:
        """Take all buffered events and clear buffer.

        Returns:
            List of buffered events
        """
        events = self._buffer.copy()
        self._buffer.clear()
        return events

    def has_events(self) -> bool:
        """Check if buffer has events."""
        return len(self._buffer) > 0

    def close(self) -> None:
        """Mark buffer as closed."""
        self._closed = True


class FallbackWriter:
    """Writes logs to local file when Elasticsearch is unavailable.

    **Feature: observability-infrastructure**
    **Requirement: R1.3 - Fallback to local file on failure**
    """

    def __init__(self, fallback_path: Path | str) -> None:
        """Initialize fallback writer.

        Args:
            fallback_path: Path for fallback log file
        """
        self._path = Path(fallback_path) if isinstance(fallback_path, str) else fallback_path
        self._logger = logging.getLogger(__name__)

    async def write(self, events: list[dict[str, Any]]) -> None:
        """Write events to fallback file.

        Args:
            events: Events to write
        """
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)

            with self._path.open("a", encoding="utf-8") as f:
                for event in events:
                    f.write(json.dumps(event) + "\n")

        except Exception as e:
            self._logger.error(f"Failed to write fallback log: {e}")


class BulkIndexer:
    """Handles bulk indexing to Elasticsearch with error handling.

    **Feature: observability-infrastructure**
    **Requirement: R1.3 - Batched bulk indexing**
    """

    def __init__(self, index_prefix: str) -> None:
        """Initialize bulk indexer.

        Args:
            index_prefix: Prefix for index names
        """
        self._index_prefix = index_prefix
        self._logger = logging.getLogger(__name__)

    def get_index_name(self) -> str:
        """Get current index name with date suffix.

        Returns:
            Index name with date suffix (e.g., "logs-api-2025.01.02")
        """
        from datetime import datetime, UTC

        date_suffix = datetime.now(UTC).strftime("%Y.%m.%d")
        return f"{self._index_prefix}-{date_suffix}"

    async def bulk_index(
        self,
        client: AsyncElasticsearch,
        events: list[dict[str, Any]],
    ) -> None:
        """Bulk index events to Elasticsearch.

        Args:
            client: Elasticsearch client
            events: Events to index

        Raises:
            Exception: If bulk indexing fails
        """
        if not events:
            return

        index_name = self.get_index_name()

        # Build bulk request body
        operations: list[dict[str, Any]] = []
        for event in events:
            operations.append({"index": {"_index": index_name}})
            operations.append(event)

        # Execute bulk request
        response = await client.bulk(operations=operations, refresh=False)

        # Check for errors
        if response.get("errors"):
            error_count = sum(
                1
                for item in response.get("items", [])
                if "error" in item.get("index", {})
            )
            self._logger.warning(f"Bulk index had {error_count} errors")
