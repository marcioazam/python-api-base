"""Dapr service invocation.

This module handles service-to-service invocation with resiliency.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any

from core.shared.logging import get_logger
from infrastructure.dapr.client import DaprClientWrapper
from infrastructure.dapr.errors import DaprConnectionError, DaprTimeoutError

logger = get_logger(__name__)


class HttpMethod(Enum):
    """HTTP methods for service invocation."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"


@dataclass
class InvocationResponse:
    """Response from service invocation."""

    data: bytes
    status_code: int
    headers: dict[str, str]
    content_type: str


class ServiceInvoker:
    """Handles service-to-service invocation."""

    def __init__(self, client: DaprClientWrapper) -> None:
        """Initialize the service invoker.

        Args:
            client: Dapr client wrapper.
        """
        self._client = client

    async def invoke(
        self,
        app_id: str,
        method_name: str,
        data: bytes | None = None,
        http_verb: HttpMethod = HttpMethod.POST,
        headers: dict[str, str] | None = None,
        metadata: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> InvocationResponse:
        """Invoke a method on a remote service.

        Args:
            app_id: Target application ID.
            method_name: Method name to invoke.
            data: Request body data.
            http_verb: HTTP method.
            headers: Additional headers.
            metadata: Dapr metadata.
            timeout: Request timeout in seconds.

        Returns:
            InvocationResponse with response data.
        """
        url = f"/v1.0/invoke/{app_id}/method/{method_name}"
        request_headers = {}

        if headers:
            request_headers.update(headers)
        if metadata:
            for key, value in metadata.items():
                request_headers[f"dapr-metadata-{key}"] = value

        # Add trace context propagation
        trace_headers = self._get_trace_headers()
        request_headers.update(trace_headers)

        try:
            response = await self._client.http_client.request(
                method=http_verb.value,
                url=url,
                content=data,
                headers=request_headers,
                timeout=timeout or self._client.settings.timeout_seconds,
            )

            logger.debug(
                "service_invoked",
                app_id=app_id,
                method=method_name,
                http_verb=http_verb.value,
                status_code=response.status_code,
            )

            return InvocationResponse(
                data=response.content,
                status_code=response.status_code,
                headers=dict(response.headers),
                content_type=response.headers.get("content-type", "application/json"),
            )
        except Exception as e:
            logger.error(
                "service_invocation_failed",
                app_id=app_id,
                method=method_name,
                error=str(e),
            )
            raise

    async def invoke_grpc(
        self,
        app_id: str,
        method_name: str,
        data: bytes,
        metadata: dict[str, str] | None = None,
    ) -> bytes:
        """Invoke a gRPC method on a remote service.

        Args:
            app_id: Target application ID.
            method_name: gRPC method name.
            data: Protobuf-encoded request data.
            metadata: gRPC metadata.

        Returns:
            Protobuf-encoded response data.
        """
        try:
            response = self._client.client.invoke_method(
                app_id=app_id,
                method_name=method_name,
                data=data,
                http_verb="POST",
            )
            return response.data
        except Exception as e:
            raise DaprConnectionError(
                message=f"gRPC invocation failed: {app_id}/{method_name}",
                details={"error": str(e)},
            ) from e

    def _get_trace_headers(self) -> dict[str, str]:
        """Get trace context headers for propagation.

        Returns:
            Dictionary of trace headers.
        """
        headers: dict[str, str] = {}

        try:
            from opentelemetry import trace
            from opentelemetry.trace.propagation.tracecontext import (
                TraceContextTextMapPropagator,
            )

            span = trace.get_current_span()
            if span.is_recording():
                propagator = TraceContextTextMapPropagator()
                propagator.inject(headers)
        except ImportError:
            pass

        return headers

    async def invoke_with_retry(
        self,
        app_id: str,
        method_name: str,
        data: bytes | None = None,
        http_verb: HttpMethod = HttpMethod.POST,
        headers: dict[str, str] | None = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ) -> InvocationResponse:
        """Invoke a method with retry logic.

        Args:
            app_id: Target application ID.
            method_name: Method name to invoke.
            data: Request body data.
            http_verb: HTTP method.
            headers: Additional headers.
            max_retries: Maximum number of retries.
            retry_delay: Delay between retries in seconds.

        Returns:
            InvocationResponse with response data.
        """
        import asyncio

        last_error: Exception | None = None

        for attempt in range(max_retries + 1):
            try:
                return await self.invoke(
                    app_id=app_id,
                    method_name=method_name,
                    data=data,
                    http_verb=http_verb,
                    headers=headers,
                )
            except (DaprConnectionError, DaprTimeoutError) as e:
                last_error = e
                if attempt < max_retries:
                    logger.warning(
                        "service_invocation_retry",
                        app_id=app_id,
                        method=method_name,
                        attempt=attempt + 1,
                        max_retries=max_retries,
                    )
                    await asyncio.sleep(retry_delay * (2**attempt))

        raise last_error or DaprConnectionError(
            message=f"Service invocation failed after {max_retries} retries"
        )
