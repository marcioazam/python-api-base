"""Example chat implementation using typed WebSocket messages.

This module demonstrates how to use the generic WebSocket types
to build a real-time chat application.

**Feature: api-architecture-analysis, Task 3.2: WebSocket Support with typed messages**
**Validates: Requirements 4.5**
"""

from datetime import datetime, UTC

from pydantic import Field

from my_api.adapters.api.websocket.types import (
    ConnectionManager,
    WebSocketConnection,
    WebSocketMessage,
    WebSocketRoute,
)


class ChatMessage(WebSocketMessage):
    """Chat message type for real-time communication."""

    type: str = "chat"
    content: str = Field(description="Message content")
    sender: str = Field(description="Sender identifier")
    room: str | None = Field(default=None, description="Target room")


class JoinRoomMessage(WebSocketMessage):
    """Message to join a chat room."""

    type: str = "join_room"
    room: str = Field(description="Room to join")


class LeaveRoomMessage(WebSocketMessage):
    """Message to leave a chat room."""

    type: str = "leave_room"
    room: str = Field(description="Room to leave")


class UserJoinedMessage(WebSocketMessage):
    """Notification when a user joins."""

    type: str = "user_joined"
    user_id: str = Field(description="User who joined")
    room: str | None = Field(default=None, description="Room joined")


class UserLeftMessage(WebSocketMessage):
    """Notification when a user leaves."""

    type: str = "user_left"
    user_id: str = Field(description="User who left")
    room: str | None = Field(default=None, description="Room left")


class ChatRoute(WebSocketRoute[ChatMessage]):
    """WebSocket route handler for chat functionality.

    Handles chat messages, room management, and user notifications.
    """

    async def on_connect(self, connection: WebSocketConnection) -> None:
        """Handle new user connection."""
        # Notify all users about the new connection
        notification = UserJoinedMessage(user_id=connection.client_id)
        await self.broadcast(notification, exclude={connection.client_id})  # type: ignore[arg-type]

    async def on_message(
        self, connection: WebSocketConnection, message: ChatMessage
    ) -> None:
        """Handle incoming chat messages.

        Routes messages based on type:
        - chat: Broadcast to room or all users
        - join_room: Add user to room
        - leave_room: Remove user from room
        """
        if message.type == "join_room":
            await self._handle_join_room(connection, message)
        elif message.type == "leave_room":
            await self._handle_leave_room(connection, message)
        else:
            await self._handle_chat_message(connection, message)

    async def on_disconnect(self, connection: WebSocketConnection) -> None:
        """Handle user disconnection."""
        notification = UserLeftMessage(user_id=connection.client_id)
        await self.broadcast(notification)  # type: ignore[arg-type]

    async def _handle_chat_message(
        self, connection: WebSocketConnection, message: ChatMessage
    ) -> None:
        """Handle a regular chat message."""
        # Set sender from connection
        message.sender = connection.client_id
        message.timestamp = datetime.now(tz=UTC)

        if message.room:
            # Send to specific room
            await self._manager.broadcast_to_room(
                message.room,
                message,
                exclude={connection.client_id},
            )
        else:
            # Broadcast to all
            await self.broadcast(message, exclude={connection.client_id})

    async def _handle_join_room(
        self, connection: WebSocketConnection, message: ChatMessage
    ) -> None:
        """Handle room join request."""
        # Extract room from message (type coercion for flexibility)
        room = getattr(message, "room", None)
        if room:
            self._manager.join_room(connection.client_id, room)
            notification = UserJoinedMessage(
                user_id=connection.client_id,
                room=room,
            )
            await self._manager.broadcast_to_room(
                room, notification, exclude={connection.client_id}  # type: ignore[arg-type]
            )

    async def _handle_leave_room(
        self, connection: WebSocketConnection, message: ChatMessage
    ) -> None:
        """Handle room leave request."""
        room = getattr(message, "room", None)
        if room:
            notification = UserLeftMessage(
                user_id=connection.client_id,
                room=room,
            )
            await self._manager.broadcast_to_room(
                room, notification, exclude={connection.client_id}  # type: ignore[arg-type]
            )
            self._manager.leave_room(connection.client_id, room)


# Pre-configured chat manager and route
chat_manager: ConnectionManager[ChatMessage] = ConnectionManager()
chat_route = ChatRoute(chat_manager, ChatMessage)
