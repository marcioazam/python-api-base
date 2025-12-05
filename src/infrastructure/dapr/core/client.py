"""Dapr client wrapper with lifecycle management.

This module provides a wrapper around the Dapr client with connection
management, error handling, and graceful shutdown support.
"""

import asyncio
from typing import Any

import httpx
from dapr.clients import DaprClient

from core.config.dapr import DaprSettings, get_dapr_settings
from core.shared.logging import get_logger
from infrastructure.dapr.errors import DaprConnectionError, DaprTimeoutError

logger = get_logger(__name__)


class DaprClientWrapper:
    """Wrapper around Dapr client with lifecycle management."""

    def __init__(self, settings: DaprSettings | None = None) -> None:
        """Initialize the Dapr client wrapper.

        Args:
            settings: Dapr configuration settings.
        """
        self._settings = settings or get_dapr_settings()
        self._client: DaprClient | None = None
        self._http_client: httpx.AsyncClient | None = None
        self._initialized = False

    @property
    def settings(self) -> DaprSettings:
        """Get Dapr settings."""
        return self._settings

    @property
    def client(self) -> DaprClient:
        """Get the underlying Dapr client.

        Raises:
            DaprConnectionError: If client is not initialized.
        """
        if self._client is None:
            raise DaprConnectionError(
                message="Dapr client not initialized",
                endpoint=self._settings.grpc_endpoint,
            )
        return self._client

    @property
    def http_client(self) -> httpx.AsyncClient:
        """Get the HTTP client for Dapr API calls.

        Raises:
            DaprConnectionError: If HTTP client is not initialized.
        """
        if self._http_client is None:
            raise DaprConnectionError(
                message="HTTP client not initialized",
                endpoint=self._settings.http_endpoint,
            )
        return self._http_client

    async def initialize(self) -> None:
        """Initialize the Dapr client and wait for sidecar if configured."""
        if self._initialized:
            return

        logger.info(
            "initializing_dapr_client",
            grpc_endpoint=self._settings.grpc_endpoint,
            http_endpoint=self._settings.http_endpoint,
        )

        if self._settings.wait_for_sidecar:
            await self._wait_for_sidecar()

        self._client = DaprClient(
            address=self._settings.grpc_endpoint,
            headers_callback=self._get_headers,
        )

        self._http_client = httpx.AsyncClient(
            base_url=self._settings.http_endpoint,
            timeout=httpx.Timeout(self._settings.timeout_seconds),
            headers=self._get_headers(),
        )

        self._initialized = True
        logger.info("dapr_client_initialized")

    async def close(self) -> None:
        """Close the Dapr client and release resources."""
        if not self._initialized:
            return

        logger.info("closing_dapr_client")

        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

        if self._client:
            self._client.close()
            self._client = None

        self._initialized = False
        logger.info("dapr_client_closed")

    def _get_headers(self) -> dict[str, str]:
        """Get headers for Dapr API calls."""
        headers: dict[str, str] = {}
        if self._settings.api_token:
            headers["dapr-api-token"] = self._settings.api_token
        return headers

    async def _wait_for_sidecar(self) -> None:
        """Wait for Dapr sidecar to be ready."""
        timeout = self._settings.sidecar_wait_timeout
        poll_interval = 0.5
        elapsed = 0.0

        logger.info(
            "waiting_for_dapr_sidecar",
            endpoint=self._settings.http_endpoint,
            timeout=timeout,
        )

        async with httpx.AsyncClient() as client:
            while elapsed < timeout:
                try:
                    response = await client.get(
                        f"{self._settings.http_endpoint}/v1.0/healthz",
                        timeout=2.0,
                    )
                    if response.status_code == 204:
                        logger.info("dapr_sidecar_ready", elapsed=elapsed)
                        return
                except httpx.RequestError:
                    pass

                await asyncio.sleep(poll_interval)
                elapsed += poll_interval

        raise DaprConnectionError(
            message=f"Dapr sidecar not ready after {timeout}s",
            endpoint=self._settings.http_endpoint,
        )

    async def invoke_method(
        self,
        app_id: str,
        method_name: str,
        data: bytes | None = None,
        http_verb: str = "POST",
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> bytes:
        """Invoke a method on a remote service.

        Args:
            app_id: Target application ID.
            method_name: Method name to invoke.
            data: Request body data.
            http_verb: HTTP method (GET, POST, PUT, DELETE, PATCH).
            headers: Additional headers.
            timeout: Request timeout in seconds.

        Returns:
            Response data as bytes.

        Raises:
            DaprConnectionError: If invocation fails.
            DaprTimeoutError: If request times out.
        """
        url = f"/v1.0/invoke/{app_id}/method/{method_name}"
        request_headers = self._get_headers()
        if headers:
            request_headers.update(headers)

        try:
            response = await self.http_client.request(
                method=http_verb,
                url=url,
                content=data,
                headers=request_headers,
                timeout=timeout or self._settings.timeout_seconds,
            )
            response.raise_for_status()
            return response.content
        except httpx.TimeoutException as e:
            raise DaprTimeoutError(
                message=f"Service invocation timed out: {app_id}/{method_name}",
                operation="invoke_method",
                timeout_seconds=timeout or self._settings.timeout_seconds,
            ) from e
        except httpx.RequestError as e:
            raise DaprConnectionError(
                message=f"Service invocation failed: {app_id}/{method_name}",
                endpoint=self._settings.http_endpoint,
                details={"error": str(e)},
            ) from e

    async def publish_event(
        self,
        pubsub_name: str,
        topic_name: str,
        data: Any,
        data_content_type: str = "application/json",
        metadata: dict[str, str] | None = None,
    ) -> None:
        """Publish an event to a topic.

        Args:
            pubsub_name: Pub/sub component name.
            topic_name: Topic name.
            data: Event data.
            data_content_type: Content type of the data.
            metadata: Additional metadata.
        """
        url = f"/v1.0/publish/{pubsub_name}/{topic_name}"
        headers = self._get_headers()
        headers["Content-Type"] = data_content_type

        if metadata:
            for key, value in metadata.items():
                headers[f"metadata.{key}"] = value

        try:
            response = await self.http_client.post(
                url,
                content=data if isinstance(data, bytes) else str(data).encode(),
                headers=headers,
            )
            response.raise_for_status()
        except httpx.RequestError as e:
            raise DaprConnectionError(
                message=f"Failed to publish event to {pubsub_name}/{topic_name}",
                endpoint=self._settings.http_endpoint,
                details={"error": str(e)},
            ) from e

    async def get_state(
        self,
        store_name: str,
        key: str,
        metadata: dict[str, str] | None = None,
    ) -> tuple[bytes | None, str | None]:
        """Get state from a state store.

        Args:
            store_name: State store component name.
            key: State key.
            metadata: Additional metadata.

        Returns:
            Tuple of (value, etag). Value is None if key doesn't exist.
        """
        url = f"/v1.0/state/{store_name}/{key}"
        headers = self._get_headers()

        if metadata:
            for k, v in metadata.items():
                headers[f"metadata.{k}"] = v

        try:
            response = await self.http_client.get(url, headers=headers)
            if response.status_code == 204:
                return None, None
            response.raise_for_status()
            etag = response.headers.get("ETag")
            return response.content, etag
        except httpx.RequestError as e:
            raise DaprConnectionError(
                message=f"Failed to get state: {store_name}/{key}",
                endpoint=self._settings.http_endpoint,
                details={"error": str(e)},
            ) from e

    async def save_state(
        self,
        store_name: str,
        key: str,
        value: bytes,
        etag: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> None:
        """Save state to a state store.

        Args:
            store_name: State store component name.
            key: State key.
            value: State value.
            etag: ETag for optimistic concurrency.
            metadata: Additional metadata.
        """
        import json

        url = f"/v1.0/state/{store_name}"
        headers = self._get_headers()
        headers["Content-Type"] = "application/json"

        state_item: dict[str, Any] = {
            "key": key,
            "value": value.decode() if isinstance(value, bytes) else value,
        }
        if etag:
            state_item["etag"] = etag
        if metadata:
            state_item["metadata"] = metadata

        try:
            response = await self.http_client.post(
                url,
                content=json.dumps([state_item]),
                headers=headers,
            )
            response.raise_for_status()
        except httpx.RequestError as e:
            raise DaprConnectionError(
                message=f"Failed to save state: {store_name}/{key}",
                endpoint=self._settings.http_endpoint,
                details={"error": str(e)},
            ) from e

    async def delete_state(
        self,
        store_name: str,
        key: str,
        etag: str | None = None,
    ) -> bool:
        """Delete state from a state store.

        Args:
            store_name: State store component name.
            key: State key.
            etag: ETag for optimistic concurrency.

        Returns:
            True if deleted, False if not found.
        """
        url = f"/v1.0/state/{store_name}/{key}"
        headers = self._get_headers()

        if etag:
            headers["If-Match"] = etag

        try:
            response = await self.http_client.delete(url, headers=headers)
            return response.status_code in (200, 204)
        except httpx.RequestError as e:
            raise DaprConnectionError(
                message=f"Failed to delete state: {store_name}/{key}",
                endpoint=self._settings.http_endpoint,
                details={"error": str(e)},
            ) from e

    async def get_secret(
        self,
        store_name: str,
        key: str,
        metadata: dict[str, str] | None = None,
    ) -> dict[str, str]:
        """Get a secret from a secret store.

        Args:
            store_name: Secret store component name.
            key: Secret key.
            metadata: Additional metadata.

        Returns:
            Dictionary of secret values.
        """
        from infrastructure.dapr.errors import SecretNotFoundError

        url = f"/v1.0/secrets/{store_name}/{key}"
        headers = self._get_headers()

        if metadata:
            for k, v in metadata.items():
                headers[f"metadata.{k}"] = v

        try:
            response = await self.http_client.get(url, headers=headers)
            if response.status_code == 404:
                raise SecretNotFoundError(
                    message=f"Secret not found: {key}",
                    store_name=store_name,
                    secret_name=key,
                )
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            raise DaprConnectionError(
                message=f"Failed to get secret: {store_name}/{key}",
                endpoint=self._settings.http_endpoint,
                details={"error": str(e)},
            ) from e


_dapr_client: DaprClientWrapper | None = None


def get_dapr_client() -> DaprClientWrapper:
    """Get the global Dapr client instance."""
    global _dapr_client
    if _dapr_client is None:
        _dapr_client = DaprClientWrapper()
    return _dapr_client


async def initialize_dapr() -> DaprClientWrapper:
    """Initialize and return the global Dapr client."""
    client = get_dapr_client()
    await client.initialize()
    return client


async def close_dapr() -> None:
    """Close the global Dapr client."""
    global _dapr_client
    if _dapr_client:
        await _dapr_client.close()
        _dapr_client = None
