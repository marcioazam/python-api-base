"""Elasticsearch client configuration and connection management.

**Feature: observability-infrastructure**
**Requirement: R2.1 - Client Configuration**
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Self

if TYPE_CHECKING:
    from elasticsearch import AsyncElasticsearch

logger = logging.getLogger(__name__)


@dataclass
class ElasticsearchClientConfig:
    """Configuration for Elasticsearch client.

    Attributes:
        hosts: List of Elasticsearch hosts
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
    username: str | None = None
    password: str | None = None
    api_key: str | tuple[str, str] | None = None
    use_ssl: bool = False
    verify_certs: bool = True
    ca_certs: str | None = None
    timeout: int = 30
    max_retries: int = 3
    retry_on_timeout: bool = True


class ElasticsearchConnection:
    """Manages Elasticsearch connection lifecycle.

    Handles connection creation, authentication, and cleanup.

    **Feature: observability-infrastructure**
    **Requirement: R2.2 - Connection Management**
    """

    def __init__(self, config: ElasticsearchClientConfig) -> None:
        """Initialize connection with configuration.

        Args:
            config: Elasticsearch client configuration
        """
        self._config = config
        self._client: AsyncElasticsearch | None = None

    async def _get_client(self) -> AsyncElasticsearch:
        """Get or create the Elasticsearch client."""
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

    @property
    def client(self) -> AsyncElasticsearch:
        """Get the raw Elasticsearch client.

        Raises:
            RuntimeError: If client is not connected
        """
        if self._client is None:
            raise RuntimeError(
                "Client not connected. Use 'async with' or call connect()"
            )
        return self._client

    async def connect(self) -> Self:
        """Connect to Elasticsearch.

        Returns:
            Self for chaining
        """
        await self._get_client()
        logger.info("Connected to Elasticsearch", extra={"hosts": self._config.hosts})
        return self

    async def close(self) -> None:
        """Close the connection."""
        if self._client:
            await self._client.close()
            self._client = None
            logger.info("Disconnected from Elasticsearch")

    async def __aenter__(self) -> Self:
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.close()

    # Health & Info Operations

    async def health(self) -> dict[str, Any]:
        """Get cluster health.

        Returns:
            Cluster health information
        """
        client = await self._get_client()
        return await client.cluster.health()

    async def info(self) -> dict[str, Any]:
        """Get cluster info.

        Returns:
            Cluster information
        """
        client = await self._get_client()
        return await client.info()

    async def ping(self) -> bool:
        """Ping the cluster.

        Returns:
            True if cluster is reachable
        """
        client = await self._get_client()
        return await client.ping()
