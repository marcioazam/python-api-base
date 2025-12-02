"""Elasticsearch handler for shipping structured logs.

Provides async log shipping to Elasticsearch with:
- Buffered batch sending
- Automatic index rotation
- Connection retry with backoff
- Fallback to local file on failure

**Feature: observability-infrastructure**
**Requirement: R1 - Structured Logging Infrastructure**
**Requirement: R2 - Generic Elasticsearch Client**
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, UTC
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from elasticsearch import AsyncElasticsearch


@dataclass
class ElasticsearchConfig:
    """Configuration for Elasticsearch connection.

    Attributes:
        hosts: List of Elasticsearch hosts
        index_prefix: Prefix for index names (e.g., "logs-api")
        batch_size: Number of logs to batch before sending
        flush_interval_seconds: Max seconds between flushes
        username: Optional username for authentication
        password: Optional password for authentication
        api_key: Optional API key for authentication
        use_ssl: Whether to use SSL/TLS
        verify_certs: Whether to verify SSL certificates
        ca_certs: Path to CA certificates
        timeout: Connection timeout in seconds
        max_retries: Maximum retry attempts
        retry_on_timeout: Whether to retry on timeout
    """

    hosts: list[str] = field(default_factory=lambda: ["http://localhost:9200"])
    index_prefix: str = "logs-python-api-base"
    batch_size: int = 100
    flush_interval_seconds: float = 5.0
    username: str | None = None
    password: str | None = None
    api_key: str | tuple[str, str] | None = None
    use_ssl: bool = False
    verify_certs: bool = True
    ca_certs: str | None = None
    timeout: int = 30
    max_retries: int = 3
    retry_on_timeout: bool = True


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
        self._fallback_path = (
            Path(fallback_path) if fallback_path else Path("logs/fallback.log")
        )
        self._buffer: list[dict[str, Any]] = []
        self._client: AsyncElasticsearch | None = None
        self._flush_task: asyncio.Task[None] | None = None
        self._closed = False
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

    def _get_index_name(self) -> str:
        """Get current index name with date suffix."""
        date_suffix = datetime.now(UTC).strftime("%Y.%m.%d")
        return f"{self._config.index_prefix}-{date_suffix}"

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
        if self._closed:
            return

        # Add timestamp if not present
        if "@timestamp" not in event and "timestamp" not in event:
            event["@timestamp"] = datetime.now(UTC).isoformat()

        self._buffer.append(event)

        # Flush if buffer is full
        if len(self._buffer) >= self._config.batch_size:
            await self.flush()

        # Start periodic flush task if not running
        if self._flush_task is None or self._flush_task.done():
            self._flush_task = asyncio.create_task(self._periodic_flush())

    async def _periodic_flush(self) -> None:
        """Periodically flush buffer."""
        while not self._closed and self._buffer:
            await asyncio.sleep(self._config.flush_interval_seconds)
            if self._buffer:
                await self.flush()

    async def flush(self) -> None:
        """Flush buffer to Elasticsearch.

        Uses bulk API for efficient indexing. Falls back to local file
        if Elasticsearch is unavailable.
        """
        if not self._buffer:
            return

        # Take buffer snapshot and clear
        events = self._buffer.copy()
        self._buffer.clear()

        try:
            await self._bulk_index(events)
            self._consecutive_failures = 0
        except Exception as e:
            self._consecutive_failures += 1
            self._logger.warning(
                f"Failed to send logs to Elasticsearch: {e}. "
                f"Consecutive failures: {self._consecutive_failures}"
            )

            # Fallback to local file
            await self._write_fallback(events)

            # Re-buffer events if we haven't hit max failures
            if self._consecutive_failures < self._max_consecutive_failures:
                self._buffer.extend(events)

    async def _bulk_index(self, events: list[dict[str, Any]]) -> None:
        """Bulk index events to Elasticsearch."""
        if not events:
            return

        client = await self._get_client()
        index_name = self._get_index_name()

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

    async def _write_fallback(self, events: list[dict[str, Any]]) -> None:
        """Write events to fallback file."""
        try:
            self._fallback_path.parent.mkdir(parents=True, exist_ok=True)

            with self._fallback_path.open("a", encoding="utf-8") as f:
                for event in events:
                    f.write(json.dumps(event) + "\n")

        except Exception as e:
            self._logger.error(f"Failed to write fallback log: {e}")

    async def close(self) -> None:
        """Close handler and flush remaining events."""
        self._closed = True

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


# Index template for ECS-compatible logs
ECS_INDEX_TEMPLATE = {
    "index_patterns": ["logs-*"],
    "template": {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 1,
            "index.lifecycle.name": "logs-policy",
            "index.lifecycle.rollover_alias": "logs",
        },
        "mappings": {
            "properties": {
                "@timestamp": {"type": "date"},
                "message": {"type": "text"},
                "log.level": {"type": "keyword"},
                "log.logger": {"type": "keyword"},
                "service.name": {"type": "keyword"},
                "service.version": {"type": "keyword"},
                "service.environment": {"type": "keyword"},
                "trace.id": {"type": "keyword"},
                "correlation_id": {"type": "keyword"},
                "request_id": {"type": "keyword"},
                "span_id": {"type": "keyword"},
                "http.method": {"type": "keyword"},
                "http.status_code": {"type": "integer"},
                "http.url": {"type": "keyword"},
                "http.path": {"type": "keyword"},
                "user.id": {"type": "keyword"},
                "error.message": {"type": "text"},
                "error.type": {"type": "keyword"},
                "error.stack_trace": {"type": "text"},
            }
        },
    },
}


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
