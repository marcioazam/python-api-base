"""streaming configuration.

**Feature: shared-modules-code-review-fixes, Task 10.2**
**Validates: Requirements 3.4**
"""

from dataclasses import dataclass

from .enums import StreamFormat


@dataclass
class StreamConfig:
    """Streaming configuration.

    Attributes:
        format: Output format.
        chunk_size: Size of chunks in bytes.
        flush_interval_ms: Interval between flushes in milliseconds.
        heartbeat_interval_ms: SSE heartbeat interval.
        max_buffer_size: Maximum buffer size before flush.
    """

    format: StreamFormat = StreamFormat.JSON_LINES
    chunk_size: int = 8192
    flush_interval_ms: int = 100
    heartbeat_interval_ms: int = 15000
    max_buffer_size: int = 65536
