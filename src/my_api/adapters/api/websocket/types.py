"""Generic WebSocket types for real-time communication.

This module provides type-safe WebSocket abstractions including
typed messages, connection management, and route handlers.

**Feature: api-architecture-analysis, Task 3.2: WebSocket Support with typed messages**
**Validates: Requirements 4.5**

Usage:
    from my_api.adapters.api.websocket import WebSocketMessage, WebSocketRoute

    class ChatMessage(WebSocketMessage):
        content: str
        sender: str

    class ChatRoute(WebSocketRoute[ChatMessage]):
        async def on_message(self, message: ChatMessage) -> None:
            await self.broadcast(message)
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Generic, TypeVar

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

MessageT = TypeVar("MessageT", bound="WebSocketMessage")


class MessageType(str, Enum):
    """Standard WebSocket message types."""

    TEXT = "text"
    BINARY = "binary"
    PING = "ping"
    PONG = "pong"
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    ERROR = "error"
    BROADCAST = "broadcast"


class WebSocketMessage(BaseModel):
    """Base class for typed WebSocket messages.

    All WebSocket messages should inherit from this class
    to ensure type safety and consistent serialization.
    """

    type: str = Field(default="message", description="Message type identifier")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(tz=timezone.utc),
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


@dataclass
class WebSocketConnection:
    """Represents an active WebSocket connection."""

    websocket: WebSocket
    client_id: str
    connected_at: datetime = field(
        default_factory=lambda: datetime.now(tz=timezone.utc)
    )
    metadata: dict[str, Any] = field(default_factory=dict)

    async def send_message(self, message: WebSocketMessage) -> None:
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


class ConnectionManager(Generic[MessageT]):
    """Manages WebSocket connections with typed messages.

    Provides connection tracking, broadcasting, and room-based
    messaging capabilities.

    Type Parameters:
        MessageT: The message type for this manager.
    """

    def __init__(self) -> None:
        """Initialize the connection manager."""
        self._connections: dict[str, WebSocketConnection] = {}
        self._rooms: dict[str, set[str]] = {}

    @property
    def connection_count(self) -> int:
        """Get the number of active connections."""
        return len(self._connections)

    @property
    def connections(self) -> list[WebSocketConnection]:
        """Get all active connections."""
        return list(self._connections.values())

    async def connect(
        self,
        websocket: WebSocket,
        client_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> WebSocketConnection:
        """Accept and register a new WebSocket connection.

        Args:
            websocket: The WebSocket instance.
            client_id: Unique identifier for the client.
            metadata: Optional metadata for the connection.

        Returns:
            The created WebSocketConnection.
        """
        await websocket.accept()
        connection = WebSocketConnection(
            websocket=websocket,
            client_id=client_id,
            metadata=metadata or {},
        )
        self._connections[client_id] = connection
        return connection

    async def disconnect(self, client_id: str) -> None:
        """Remove a connection from the manager.

        Args:
            client_id: The client identifier to disconnect.
        """
        if client_id in self._connections:
            # Remove from all rooms
            for room_clients in self._rooms.values():
                room_clients.discard(client_id)
            del self._connections[client_id]

    def get_connection(self, client_id: str) -> WebSocketConnection | None:
        """Get a connection by client ID.

        Args:
            client_id: The client identifier.

        Returns:
            The connection if found, None otherwise.
        """
        return self._connections.get(client_id)

    async def send_personal(self, client_id: str, message: MessageT) -> bool:
        """Send a message to a specific client.

        Args:
            client_id: The target client identifier.
            message: The message to send.

        Returns:
            True if sent successfully, False if client not found.
        """
        connection = self._connections.get(client_id)
        if connection:
            await connection.send_message(message)
            return True
        return False

    async def broadcast(
        self,
        message: MessageT,
        exclude: set[str] | None = None,
    ) -> int:
        """Broadcast a message to all connected clients.

        Args:
            message: The message to broadcast.
            exclude: Optional set of client IDs to exclude.

        Returns:
            Number of clients the message was sent to.
        """
        exclude = exclude or set()
        sent_count = 0

        for client_id, connection in self._connections.items():
            if client_id not in exclude:
                try:
                    await connection.send_message(message)
                    sent_count += 1
                except Exception:
                    # Connection might be closed
                    pass

        return sent_count

    # Room management
    def join_room(self, client_id: str, room: str) -> bool:
        """Add a client to a room.

        Args:
            client_id: The client identifier.
            room: The room name.

        Returns:
            True if joined successfully.
        """
        if client_id not in self._connections:
            return False

        if room not in self._rooms:
            self._rooms[room] = set()
        self._rooms[room].add(client_id)
        return True

    def leave_room(self, client_id: str, room: str) -> bool:
        """Remove a client from a room.

        Args:
            client_id: The client identifier.
            room: The room name.

        Returns:
            True if left successfully.
        """
        if room in self._rooms:
            self._rooms[room].discard(client_id)
            if not self._rooms[room]:
                del self._rooms[room]
            return True
        return False

    def get_room_members(self, room: str) -> set[str]:
        """Get all client IDs in a room.

        Args:
            room: The room name.

        Returns:
            Set of client IDs in the room.
        """
        return self._rooms.get(room, set()).copy()

    async def broadcast_to_room(
        self,
        room: str,
        message: MessageT,
        exclude: set[str] | None = None,
    ) -> int:
        """Broadcast a message to all clients in a room.

        Args:
            room: The room name.
            message: The message to broadcast.
            exclude: Optional set of client IDs to exclude.

        Returns:
            Number of clients the message was sent to.
        """
        exclude = exclude or set()
        room_members = self._rooms.get(room, set())
        sent_count = 0

        for client_id in room_members:
            if client_id not in exclude:
                connection = self._connections.get(client_id)
                if connection:
                    try:
                        await connection.send_message(message)
                        sent_count += 1
                    except Exception:
                        pass

        return sent_count


class WebSocketRoute(ABC, Generic[MessageT]):
    """Abstract base class for typed WebSocket routes.

    Provides a structured way to handle WebSocket connections
    with typed messages and lifecycle hooks.

    Type Parameters:
        MessageT: The message type for this route.
    """

    def __init__(
        self,
        manager: ConnectionManager[MessageT],
        message_class: type[MessageT],
    ) -> None:
        """Initialize the WebSocket route.

        Args:
            manager: The connection manager.
            message_class: The message class for deserialization.
        """
        self._manager = manager
        self._message_class = message_class

    @property
    def manager(self) -> ConnectionManager[MessageT]:
        """Get the connection manager."""
        return self._manager

    async def handle_connection(
        self,
        websocket: WebSocket,
        client_id: str,
        **kwargs: Any,
    ) -> None:
        """Handle a WebSocket connection lifecycle.

        This method manages the full connection lifecycle:
        1. Accept connection
        2. Call on_connect hook
        3. Listen for messages
        4. Call on_disconnect hook on close

        Args:
            websocket: The WebSocket instance.
            client_id: Unique client identifier.
            **kwargs: Additional connection parameters.
        """
        connection = await self._manager.connect(
            websocket, client_id, metadata=kwargs
        )

        try:
            await self.on_connect(connection)

            while True:
                data = await websocket.receive_text()
                try:
                    message = self._message_class.model_validate_json(data)
                    await self.on_message(connection, message)
                except Exception as e:
                    error = ErrorMessage(
                        code="INVALID_MESSAGE",
                        message=str(e),
                    )
                    await connection.send_message(error)

        except WebSocketDisconnect:
            pass
        finally:
            await self._manager.disconnect(client_id)
            await self.on_disconnect(connection)

    async def on_connect(self, connection: WebSocketConnection) -> None:
        """Called when a client connects.

        Override to implement custom connection logic.

        Args:
            connection: The new connection.
        """
        pass

    @abstractmethod
    async def on_message(
        self, connection: WebSocketConnection, message: MessageT
    ) -> None:
        """Called when a message is received.

        Must be implemented by subclasses.

        Args:
            connection: The connection that sent the message.
            message: The received message.
        """
        ...

    async def on_disconnect(self, connection: WebSocketConnection) -> None:
        """Called when a client disconnects.

        Override to implement custom disconnection logic.

        Args:
            connection: The disconnected connection.
        """
        pass

    async def broadcast(
        self,
        message: MessageT,
        exclude: set[str] | None = None,
    ) -> int:
        """Broadcast a message to all connected clients.

        Args:
            message: The message to broadcast.
            exclude: Optional set of client IDs to exclude.

        Returns:
            Number of clients the message was sent to.
        """
        return await self._manager.broadcast(message, exclude)

    async def send_to(self, client_id: str, message: MessageT) -> bool:
        """Send a message to a specific client.

        Args:
            client_id: The target client identifier.
            message: The message to send.

        Returns:
            True if sent successfully.
        """
        return await self._manager.send_personal(client_id, message)


def create_websocket_endpoint(
    route: WebSocketRoute[MessageT],
) -> Callable:
    """Create a FastAPI WebSocket endpoint from a route.

    Args:
        route: The WebSocket route handler.

    Returns:
        A FastAPI-compatible WebSocket endpoint function.

    Example:
        manager = ConnectionManager[ChatMessage]()
        chat_route = ChatRoute(manager, ChatMessage)

        @app.websocket("/ws/chat/{client_id}")
        async def chat_endpoint(websocket: WebSocket, client_id: str):
            await chat_route.handle_connection(websocket, client_id)
    """

    async def endpoint(websocket: WebSocket, client_id: str) -> None:
        await route.handle_connection(websocket, client_id)

    return endpoint
