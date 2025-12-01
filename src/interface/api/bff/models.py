"""bff models."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from .enums import ClientType

if TYPE_CHECKING:
    from .service import HandlerFunc, ClientInfo


@dataclass
class BFFRoute[RequestT, ResponseT]:
    """A BFF route with client-specific handlers."""

    path: str
    method: str
    default_handler: HandlerFunc[RequestT, ResponseT]
    client_handlers: dict[ClientType, HandlerFunc[RequestT, ResponseT]] = field(
        default_factory=dict
    )

    def add_handler(
        self,
        client_type: ClientType,
        handler: HandlerFunc[RequestT, ResponseT],
    ) -> "BFFRoute[RequestT, ResponseT]":
        """Add a client-specific handler."""
        self.client_handlers[client_type] = handler
        return self

    def get_handler(self, client_type: ClientType) -> HandlerFunc[RequestT, ResponseT]:
        """Get the appropriate handler for the client type."""
        return self.client_handlers.get(client_type, self.default_handler)

    async def handle(self, request: RequestT, client_info: ClientInfo) -> ResponseT:
        """Handle the request with the appropriate handler."""
        handler = self.get_handler(client_info.client_type)
        return await handler(request, client_info)
