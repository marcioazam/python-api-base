"""RabbitMQ RPC client implementation.

**Feature: enterprise-generics-2025**
**Requirement: R3.5 - Generic_RpcClient[TRequest, TResponse].call()**
**Refactored: 2025 - Extracted from rabbitmq.py for SRP compliance**
"""

from __future__ import annotations

import asyncio
from datetime import timedelta
from uuid import uuid4

from pydantic import BaseModel

from infrastructure.tasks.rabbitmq.config import RabbitMQConfig


class RabbitMQRpcClient[TRequest: BaseModel, TResponse: BaseModel]:
    """RabbitMQ RPC client with typed request/response.

    **Requirement: R3.5 - Generic_RpcClient[TRequest, TResponse].call()**

    Type Parameters:
        TRequest: Request type.
        TResponse: Response type.
    """

    def __init__(
        self,
        config: RabbitMQConfig,
        response_type: type[TResponse],
        timeout: timedelta = timedelta(seconds=30),
    ) -> None:
        """Initialize RPC client.

        Args:
            config: RabbitMQ configuration.
            response_type: Expected response type.
            timeout: RPC timeout.
        """
        self._config = config
        self._response_type = response_type
        self._timeout = timeout
        self._pending: dict[str, asyncio.Future[TResponse]] = {}

    async def call(self, request: TRequest) -> TResponse:
        """Make RPC call.

        **Requirement: R3.5 - call(request) returns Awaitable[TResponse]**

        Args:
            request: Request payload.

        Returns:
            Response from server.

        Raises:
            TimeoutError: If timeout exceeded.
        """
        correlation_id = str(uuid4())
        future: asyncio.Future[TResponse] = asyncio.Future()
        self._pending[correlation_id] = future

        try:
            # In real implementation, publish to RPC queue
            # and wait for response on reply queue
            return await asyncio.wait_for(
                future,
                timeout=self._timeout.total_seconds(),
            )
        except TimeoutError as e:
            raise TimeoutError(f"RPC call timed out after {self._timeout}") from e
        finally:
            self._pending.pop(correlation_id, None)

    def _handle_response(self, correlation_id: str, response: TResponse) -> None:
        """Handle RPC response (called internally)."""
        if correlation_id in self._pending:
            self._pending[correlation_id].set_result(response)
