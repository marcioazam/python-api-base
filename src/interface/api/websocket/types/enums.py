"""types enums."""

from enum import Enum


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
