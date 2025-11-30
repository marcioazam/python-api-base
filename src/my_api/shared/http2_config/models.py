"""http2_config models."""

from dataclasses import dataclass


@dataclass
class ConnectionStats:
    """HTTP/2 connection statistics."""

    streams_opened: int = 0
    streams_closed: int = 0
    frames_sent: int = 0
    frames_received: int = 0
    bytes_sent: int = 0
    bytes_received: int = 0
    push_promises_sent: int = 0
    goaway_sent: bool = False
    goaway_received: bool = False
    last_stream_id: int = 0

    def record_stream_open(self) -> None:
        """Record stream opening."""
        self.streams_opened += 1

    def record_stream_close(self) -> None:
        """Record stream closing."""
        self.streams_closed += 1

    def record_frame_sent(self, size: int) -> None:
        """Record frame sent."""
        self.frames_sent += 1
        self.bytes_sent += size

    def record_frame_received(self, size: int) -> None:
        """Record frame received."""
        self.frames_received += 1
        self.bytes_received += size

    @property
    def active_streams(self) -> int:
        """Get number of active streams."""
        return self.streams_opened - self.streams_closed
