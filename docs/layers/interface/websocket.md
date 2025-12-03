# WebSocket

## Overview

WebSocket handlers para comunicação bidirecional em tempo real.

## Connection Manager

```python
from fastapi import WebSocket
from dataclasses import dataclass, field

@dataclass
class ConnectionManager:
    """Manage WebSocket connections."""
    
    connections: dict[str, WebSocket] = field(default_factory=dict)
    
    async def connect(self, websocket: WebSocket, client_id: str) -> None:
        await websocket.accept()
        self.connections[client_id] = websocket
    
    def disconnect(self, client_id: str) -> None:
        self.connections.pop(client_id, None)
    
    async def send_personal(self, client_id: str, message: dict) -> None:
        if client_id in self.connections:
            await self.connections[client_id].send_json(message)
    
    async def broadcast(self, message: dict, exclude: str | None = None) -> None:
        for client_id, connection in self.connections.items():
            if client_id != exclude:
                await connection.send_json(message)

manager = ConnectionManager()
```

## WebSocket Endpoint

```python
from fastapi import WebSocket, WebSocketDisconnect, Depends

@router.websocket("/ws/{client_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    client_id: str,
    token: str = Query(...),
):
    # Authenticate
    try:
        user = await authenticate_websocket(token)
    except AuthError:
        await websocket.close(code=4001)
        return
    
    # Connect
    await manager.connect(websocket, client_id)
    
    try:
        while True:
            data = await websocket.receive_json()
            await handle_message(client_id, data)
    except WebSocketDisconnect:
        manager.disconnect(client_id)
        await manager.broadcast({"type": "user_left", "user_id": client_id})
```

## Message Handling

```python
async def handle_message(client_id: str, data: dict) -> None:
    message_type = data.get("type")
    
    match message_type:
        case "chat":
            await handle_chat_message(client_id, data)
        case "typing":
            await handle_typing_indicator(client_id, data)
        case "ping":
            await manager.send_personal(client_id, {"type": "pong"})
        case _:
            await manager.send_personal(client_id, {
                "type": "error",
                "message": f"Unknown message type: {message_type}",
            })

async def handle_chat_message(client_id: str, data: dict) -> None:
    message = {
        "type": "chat",
        "from": client_id,
        "content": data.get("content"),
        "timestamp": datetime.utcnow().isoformat(),
    }
    await manager.broadcast(message)
```

## Room-Based Communication

```python
@dataclass
class RoomManager:
    """Manage WebSocket rooms."""
    
    rooms: dict[str, set[str]] = field(default_factory=dict)
    connections: dict[str, WebSocket] = field(default_factory=dict)
    
    async def join_room(self, client_id: str, room_id: str) -> None:
        if room_id not in self.rooms:
            self.rooms[room_id] = set()
        self.rooms[room_id].add(client_id)
    
    async def leave_room(self, client_id: str, room_id: str) -> None:
        if room_id in self.rooms:
            self.rooms[room_id].discard(client_id)
    
    async def broadcast_to_room(self, room_id: str, message: dict) -> None:
        if room_id not in self.rooms:
            return
        for client_id in self.rooms[room_id]:
            if client_id in self.connections:
                await self.connections[client_id].send_json(message)
```

## Authentication

```python
async def authenticate_websocket(token: str) -> User:
    """Authenticate WebSocket connection."""
    try:
        payload = jwt_service.verify(token)
        user = await user_repository.get(payload.user_id)
        if not user:
            raise AuthError("User not found")
        return user
    except JWTError:
        raise AuthError("Invalid token")
```

## Best Practices

1. **Authenticate on connect** - Validate token before accepting
2. **Handle disconnects** - Clean up resources
3. **Use rooms** - For group communication
4. **Implement heartbeat** - Detect dead connections
5. **Rate limit messages** - Prevent spam
