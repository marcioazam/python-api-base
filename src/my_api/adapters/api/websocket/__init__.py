"""WebSocket adapter module with typed message support.

This module provides generic WebSocket types and utilities for building
type-safe real-time communication with FastAPI.

**Feature: api-architecture-analysis, Task 3.2: WebSocket Support with typed messages**
**Validates: Requirements 4.5**
"""

from my_api.adapters.api.websocket.types import (
    ConnectionManager,
    WebSocketMessage,
    WebSocketRoute,
)

__all__ = [
    "ConnectionManager",
    "WebSocketMessage",
    "WebSocketRoute",
]
