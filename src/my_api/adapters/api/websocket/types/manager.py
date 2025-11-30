"""WebSocket connection manager and routes.

Feature: file-size-compliance-phase2
"""

from abc import ABC, abstractmethod
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from .messages import ErrorMessage, WebSocketMessage
from .models import WebSocketConnection


class ConnectionManager[MessageT: WebSocketMessage]:
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

        Validates client_id uniqueness before accepting. If a connection
        with the same client_id already exists, it will be disconnected
        first to ensure uniqueness.

        Args:
            websocket: The WebSocket instance.
            client_id: Unique identifier for the client.
            metadata: Optional metadata for the connection.

        Returns:
            The created WebSocketConnection.
        """
        # Ensure client_id uniqueness - disconnect existing if present
        if client_id in self._connections:
            await self.disconnect(client_id)

        await websocket.accept()
        connection = WebSocketConnection(
            websocket=websocket,
            client_id=client_id,
            metadata=metadata or {},
        )
        self._connections[client_id] = connection
        return connection

    async def disconnect(self, client_id: str) -> None:
        """Remove a connection from the manager atomically.

        Removes the client from all rooms and cleans up empty rooms
        to prevent memory leaks.

        Args:
            client_id: The client identifier to disconnect.
        """
        if client_id in self._connections:
            # Remove from all rooms and cleanup empty rooms
            empty_rooms = []
            for room_name, room_clients in self._rooms.items():
                room_clients.discard(client_id)
                if not room_clients:
                    empty_rooms.append(room_name)

            # Delete empty rooms to prevent memory leaks
            for room_name in empty_rooms:
                del self._rooms[room_name]

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

class WebSocketRoute[MessageT: WebSocketMessage](ABC):
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

