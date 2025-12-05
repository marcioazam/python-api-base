"""Dapr input/output bindings.

This module provides bindings integration with external systems.
"""

import json
from dataclasses import dataclass
from typing import Any, Callable, Awaitable

from core.shared.logging import get_logger
from infrastructure.dapr.client import DaprClientWrapper
from infrastructure.dapr.errors import DaprConnectionError

logger = get_logger(__name__)


@dataclass
class BindingRequest:
    """Request for output binding invocation."""

    data: Any
    operation: str
    metadata: dict[str, str] | None = None


@dataclass
class BindingResponse:
    """Response from binding invocation."""

    data: bytes | None
    metadata: dict[str, str] | None


@dataclass
class InputBindingEvent:
    """Event from input binding."""

    binding_name: str
    data: Any
    metadata: dict[str, str] | None


class BindingsManager:
    """Manages input/output bindings."""

    def __init__(self, client: DaprClientWrapper) -> None:
        """Initialize the bindings manager.

        Args:
            client: Dapr client wrapper.
        """
        self._client = client
        self._handlers: dict[
            str, Callable[[InputBindingEvent], Awaitable[dict[str, Any] | None]]
        ] = {}

    async def invoke_binding(
        self,
        binding_name: str,
        operation: str,
        data: Any = None,
        metadata: dict[str, str] | None = None,
    ) -> BindingResponse:
        """Invoke an output binding.

        Args:
            binding_name: Binding component name.
            operation: Binding operation (e.g., "create", "get").
            data: Data to send.
            metadata: Additional metadata.

        Returns:
            BindingResponse with response data.
        """
        url = f"/v1.0/bindings/{binding_name}"
        headers = {"Content-Type": "application/json"}

        payload: dict[str, Any] = {"operation": operation}
        if data is not None:
            payload["data"] = data
        if metadata:
            payload["metadata"] = metadata

        try:
            response = await self._client.http_client.post(
                url,
                content=json.dumps(payload),
                headers=headers,
            )
            response.raise_for_status()

            logger.debug(
                "binding_invoked",
                binding=binding_name,
                operation=operation,
            )

            return BindingResponse(
                data=response.content if response.content else None,
                metadata=dict(response.headers),
            )
        except Exception as e:
            raise DaprConnectionError(
                message=f"Failed to invoke binding {binding_name}",
                details={"operation": operation, "error": str(e)},
            ) from e

    def register_handler(
        self,
        binding_name: str,
        handler: Callable[[InputBindingEvent], Awaitable[dict[str, Any] | None]],
    ) -> None:
        """Register a handler for input binding events.

        Args:
            binding_name: Binding component name.
            handler: Async handler function.
        """
        self._handlers[binding_name] = handler
        logger.info("binding_handler_registered", binding=binding_name)

    async def handle_event(
        self,
        binding_name: str,
        data: Any,
        metadata: dict[str, str] | None = None,
    ) -> dict[str, Any] | None:
        """Handle an input binding event.

        Args:
            binding_name: Binding component name.
            data: Event data.
            metadata: Event metadata.

        Returns:
            Optional response data.
        """
        handler = self._handlers.get(binding_name)
        if not handler:
            logger.warning("no_handler_for_binding", binding=binding_name)
            return None

        event = InputBindingEvent(
            binding_name=binding_name,
            data=data,
            metadata=metadata,
        )

        try:
            return await handler(event)
        except Exception as e:
            logger.error(
                "binding_handler_error",
                binding=binding_name,
                error=str(e),
            )
            raise

    def get_registered_bindings(self) -> list[str]:
        """Get list of registered binding handlers.

        Returns:
            List of binding names.
        """
        return list(self._handlers.keys())
