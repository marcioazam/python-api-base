"""types models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import TYPE_CHECKING, Any

from fastapi import WebSocket

if TYPE_CHECKING:
    from .messages import WebSocketMessage


@dataclass
class WebSocketConnection:
    """Represents an active WebSocket connection."""

    websocket: WebSocket
    client_id: str
    connected_at: datetime = field(
        default_factory=lambda: datetime.now(tz=UTC)
    )
    metadata: dict[str, Any] = field(default_factory=dict)

    async def send_message(self, message: "WebSocketMessage") -> None:
        """Send a typed message to this connection."""
        await self.websocket.send_text(message.to_json())

    async def send_json(self, data: dict[str, Any]) -> None:
        """Send raw JSON data to this connection."""
        await self.websocket.send_json(data)

    async def send_text(self, text: str) -> None:
        """Send raw text to this connection."""
        await self.websocket.send_text(text)

    async def close(self, code: int = 1000, reason: str = "") -> None:
        """Close the connection."""
        await self.websocket.close(code=code, reason=reason)
