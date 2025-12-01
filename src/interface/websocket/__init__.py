"""WebSocket adapter module with typed message support.

This module provides generic WebSocket types and utilities for building
type-safe real-time communication with FastAPI.

**Feature: api-architecture-analysis, Task 3.2: WebSocket Support with typed messages**
**Feature: interface-layer-generics-review**
**Validates: Requirements 4.5, 7.1, 7.3, 7.4, 7.5**
"""

from interface.websocket.types.manager import (
    ConnectionManager,
    WebSocketRoute,
)
from interface.websocket.types.messages import (
    WebSocketMessage,
    ErrorMessage,
)

__all__ = [
    "ConnectionManager",
    "WebSocketMessage",
    "WebSocketRoute",
    "ErrorMessage",
]
