# WebSocket API Documentation

## Overview

Python API Base provides WebSocket endpoints for real-time bidirectional communication.

## Endpoint

```
ws://localhost:8000/ws/{channel}
```

## Authentication

Include JWT token as query parameter:

```
ws://localhost:8000/ws/chat?token=<access_token>
```

## Message Format

### Client to Server

```json
{
  "type": "message",
  "channel": "chat",
  "data": {
    "content": "Hello, world!"
  }
}
```

### Server to Client

```json
{
  "type": "message",
  "channel": "chat",
  "data": {
    "content": "Hello, world!",
    "sender": "user123",
    "timestamp": "2024-01-01T00:00:00Z"
  }
}
```

## Message Types

| Type | Direction | Description |
|------|-----------|-------------|
| `connect` | S→C | Connection established |
| `disconnect` | S→C | Connection closed |
| `message` | Both | Chat message |
| `typing` | C→S | User typing indicator |
| `presence` | S→C | User presence update |
| `error` | S→C | Error notification |

## Channels

| Channel | Description |
|---------|-------------|
| `chat` | General chat |
| `notifications` | User notifications |
| `updates` | Real-time updates |

## Connection Lifecycle

1. Client connects with token
2. Server validates token
3. Server sends `connect` message
4. Bidirectional communication
5. Client/Server sends `disconnect`

## Error Handling

```json
{
  "type": "error",
  "data": {
    "code": "UNAUTHORIZED",
    "message": "Invalid token"
  }
}
```

## Related

- [REST API](../rest/index.md)
- [Authentication](../security.md)
