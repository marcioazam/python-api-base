"""WebSocket message types.

Feature: file-size-compliance-phase2
"""

from datetime import datetime, UTC
from typing import Any

from pydantic import BaseModel, Field



class WebSocketMessage(BaseModel):
    """Base class for typed WebSocket messages.

    All WebSocket messages should inherit from this class
    to ensure type safety and consistent serialization.
    """

    type: str = Field(default="message", description="Message type identifier")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC),
        description="Message timestamp",
    )

    model_config = {"extra": "allow"}

    def to_json(self) -> str:
        """Serialize message to JSON string."""
        return self.model_dump_json()

    @classmethod
    def from_json(cls, data: str) -> "WebSocketMessage":
        """Deserialize message from JSON string."""
        return cls.model_validate_json(data)

class SystemMessage(WebSocketMessage):
    """System-level WebSocket message."""

    type: str = "system"
    event: str = Field(description="System event type")
    data: dict[str, Any] = Field(default_factory=dict)

class ErrorMessage(WebSocketMessage):
    """Error message for WebSocket communication."""

    type: str = "error"
    code: str = Field(description="Error code")
    message: str = Field(description="Error message")
    details: dict[str, Any] | None = Field(default=None)

