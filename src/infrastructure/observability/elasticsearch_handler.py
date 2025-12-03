"""Elasticsearch handler for shipping structured logs.

Main handler interface that composes configuration, buffering, and indexing.

**Feature: observability-infrastructure**
**Requirement: R1 - Structured Logging Infrastructure**
**Requirement: R2 - Generic Elasticsearch Client**
**Refactored: 2025 - Split into modular components for maintainability**
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Sequence
from datetime import datetime, UTC
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from infrastructure.observability.elasticsearch_config import (
    ElasticsearchConfig,
    ECS_INDEX_TEMPLATE,
)
from infrastructure.observability.elasticsearch_buffer import (
    LogBuffer,
    FallbackWriter,
    BulkIndexer,
)

if TYPE_CHECKING:
    from elasticsearch import AsyncElasticsearch


@runtime_checkable
class LogHandler(Protocol):
    """Protocol for log handlers."""

    async def emit(self, event: dict[str, Any]) -> None:
        """Emit a log event."""
        ...

    async def flush(self) -> None:
        """Flush buffered events."""
        ...

    async def close(self) -> None:
        """Close the handler."""
        ...


class ElasticsearchHandler:
    """Async Elasticsearch handler for structured logs.

    Features:
    - Batched bulk indexing
    - Automatic index rotation (daily)
    - Connection retry with exponential backoff
    - Fallback to local file on persistent failure
    - ILM (Index Lifecycle Management) support

    **Feature: observability-infrastructure**
    **Requirement: R1.3 - Ship logs to Elasticsearch**

    Example:
        >>> config = ElasticsearchConfig(hosts=["http://localhost:9200"])
        >>> handler = ElasticsearchHandler(config)
        >>> await handler.emit({"message": "Hello", "level": "INFO"})
        >>> await handler.flush()
        >>> await handler.close()
    """

    def __init__(
        self,
        config: ElasticsearchConfig,
        fallback_path: Path | str | None = None,
    ) -> None:
        """Initialize Elasticsearch handler.

        Args:
            config: Elasticsearch configuration
            fallback_path: Path for fallback file when ES is unavailable
        """
        self._config = config
        self._buffer = LogBuffer(
            batch_size=config.batch_size,
            flush_interval_seconds=config.flush_interval_seconds,
        )
        self._fallback = FallbackWriter(
            fallback_path or Path("logs/fallback.log")
        )
        self._indexer = BulkIndexer(config.index_prefix)
        self._client: AsyncElasticsearch | None = None
        self._flush_task: asyncio.Task[None] | None = None
        self._logger = logging.getLogger(__name__)
        self._consecutive_failures = 0
        self._max_consecutive_failures = 5

    async def _get_client(self) -> AsyncElasticsearch:
        """Get or create Elasticsearch client."""
        if self._client is None:
            from elasticsearch import AsyncElasticsearch

            # Build auth params
            auth_params: dict[str, Any] = {}
            if self._config.api_key:
                auth_params["api_key"] = self._config.api_key
            elif self._config.username and self._config.password:
                auth_params["basic_auth"] = (
                    self._config.username,
                    self._config.password,
                )

            # Build SSL params
            ssl_params: dict[str, Any] = {}
            if self._config.use_ssl:
                ssl_params["use_ssl"] = True
                ssl_params["verify_certs"] = self._config.verify_certs
                if self._config.ca_certs:
                    ssl_params["ca_certs"] = self._config.ca_certs

            self._client = AsyncElasticsearch(
                hosts=self._config.hosts,
                timeout=self._config.timeout,
                max_retries=self._config.max_retries,
                retry_on_timeout=self._config.retry_on_timeout,
                **auth_params,
                **ssl_params,
            )

        return self._client

    async def emit(self, event: dict[str, Any]) -> None:
        """Add log event to buffer.

        Args:
            event: Log event dictionary

        Example:
            >>> await handler.emit({
            ...     "message": "User logged in",
            ...     "level": "INFO",
            ...     "user_id": "123",
            ... })
        """
        # Add timestamp if not present
        if "@timestamp" not in event and "timestamp" not in event:
            event["@timestamp"] = datetime.now(UTC).isoformat()

        should_flush = self._buffer.add(event)

        # Flush if buffer is full
        if should_flush:
            await self.flush()

        # Start periodic flush task if not running
        if self._flush_task is None or self._flush_task.done():
            self._flush_task = asyncio.create_task(self._periodic_flush())

    async def _periodic_flush(self) -> None:
        """Periodically flush buffer."""
        while self._buffer.has_events():
            await asyncio.sleep(self._config.flush_interval_seconds)
            if self._buffer.has_events():
                await self.flush()

    async def flush(self) -> None:
        """Flush buffer to Elasticsearch.

        Uses bulk API for efficient indexing. Falls back to local file
        if Elasticsearch is unavailable.
        """
        events = self._buffer.take_all()
        if not events:
            return

        try:
            client = await self._get_client()
            await self._indexer.bulk_index(client, events)
            self._consecutive_failures = 0
        except Exception as e:
            self._consecutive_failures += 1
            self._logger.warning(
                f"Failed to send logs to Elasticsearch: {e}. "
                f"Consecutive failures: {self._consecutive_failures}"
            )

            # Fallback to local file
            await self._fallback.write(events)

            # Re-buffer events if we haven't hit max failures
            if self._consecutive_failures < self._max_consecutive_failures:
                for event in events:
                    self._buffer.add(event)

    async def close(self) -> None:
        """Close handler and flush remaining events."""
        self._buffer.close()

        # Cancel periodic flush task
        if self._flush_task and not self._flush_task.done():
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass

        # Final flush
        await self.flush()

        # Close client
        if self._client:
            await self._client.close()
            self._client = None

    async def __aenter__(self) -> "ElasticsearchHandler":
        """Async context manager entry."""
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.close()


class ElasticsearchLogProcessor:
    """Structlog processor that ships logs to Elasticsearch.

    Can be added to structlog processor chain to automatically
    ship all logs to Elasticsearch.

    **Feature: observability-infrastructure**
    **Requirement: R1.3 - Ship logs to Elasticsearch**

    Example:
        >>> processor = ElasticsearchLogProcessor(config)
        >>> # Add to structlog processors
        >>> structlog.configure(processors=[..., processor, ...])
    """

    def __init__(
        self,
        config: ElasticsearchConfig,
        enabled: bool = True,
    ) -> None:
        """Initialize processor.

        Args:
            config: Elasticsearch configuration
            enabled: Whether to enable shipping
        """
        self._handler = ElasticsearchHandler(config) if enabled else None
        self._enabled = enabled

    def __call__(
        self,
        logger: Any,
        method_name: str,
        event_dict: dict[str, Any],
    ) -> dict[str, Any]:
        """Process log event and ship to Elasticsearch.

        This is a pass-through processor that queues the event
        for async shipping while returning it unchanged.
        """
        if self._enabled and self._handler:
            # Queue event for async shipping (fire and forget)
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._handler.emit(event_dict.copy()))
            except RuntimeError:
                # No running loop - skip shipping
                pass

        return event_dict

    async def close(self) -> None:
        """Close the handler."""
        if self._handler:
            await self._handler.close()


async def create_elasticsearch_handler(
    hosts: Sequence[str] | None = None,
    index_prefix: str = "logs-python-api-base",
    batch_size: int = 100,
    **kwargs: Any,
) -> ElasticsearchHandler:
    """Factory function to create Elasticsearch handler.

    Args:
        hosts: List of Elasticsearch hosts
        index_prefix: Prefix for index names
        batch_size: Number of logs to batch
        **kwargs: Additional config options

    Returns:
        Configured ElasticsearchHandler

    Example:
        >>> handler = await create_elasticsearch_handler(
        ...     hosts=["http://localhost:9200"],
        ...     index_prefix="logs-my-api",
        ... )
    """
    config = ElasticsearchConfig(
        hosts=list(hosts) if hosts else ["http://localhost:9200"],
        index_prefix=index_prefix,
        batch_size=batch_size,
        **kwargs,
    )
    return ElasticsearchHandler(config)


async def setup_elasticsearch_index_template(
    client: AsyncElasticsearch,
    template_name: str = "logs-template",
) -> None:
    """Set up ECS-compatible index template.

    Args:
        client: Elasticsearch client
        template_name: Name for the template
    """
    await client.indices.put_index_template(
        name=template_name,
        **ECS_INDEX_TEMPLATE,
    )
