"""streaming service."""

import asyncio
import json
from datetime import datetime, UTC
from typing import Any
from collections.abc import AsyncIterator, Callable
from pydantic import BaseModel
from .enums import StreamFormat
from .models import SSEEvent
from .config import StreamConfig


class StreamStats(BaseModel):
    """Streaming statistics.

    Attributes:
        bytes_sent: Total bytes sent.
        chunks_sent: Number of chunks sent.
        events_sent: Number of SSE events sent.
        start_time: Stream start time.
        duration_ms: Stream duration in milliseconds.
    """

    bytes_sent: int = 0
    chunks_sent: int = 0
    events_sent: int = 0
    start_time: datetime | None = None
    duration_ms: float = 0.0

class StreamingResponse[T]:
    """Generic streaming response.

    Provides streaming of data with configurable format and chunking.
    """

    def __init__(
        self,
        source: AsyncIterator[T],
        serializer: Callable[[T], str] | None = None,
        config: StreamConfig | None = None,
    ) -> None:
        """Initialize streaming response.

        Args:
            source: Async iterator of items to stream.
            serializer: Function to serialize items to string.
            config: Streaming configuration.
        """
        self._source = source
        self._serializer = serializer or (lambda x: json.dumps(x) if not isinstance(x, str) else x)
        self._config = config or StreamConfig()
        self._stats = StreamStats()
        self._closed = False

    async def __aiter__(self) -> AsyncIterator[bytes]:
        """Iterate over stream chunks.

        Yields:
            Encoded chunks.
        """
        self._stats.start_time = datetime.now(UTC)

        try:
            async for item in self._source:
                if self._closed:
                    break

                chunk = self._format_item(item)
                encoded = chunk.encode("utf-8")

                self._stats.bytes_sent += len(encoded)
                self._stats.chunks_sent += 1

                yield encoded

        finally:
            end_time = datetime.now(UTC)
            if self._stats.start_time:
                self._stats.duration_ms = (
                    end_time - self._stats.start_time
                ).total_seconds() * 1000

    def _format_item(self, item: T) -> str:
        """Format item according to stream format.

        Args:
            item: Item to format.

        Returns:
            Formatted string.
        """
        serialized = self._serializer(item)

        if self._config.format == StreamFormat.JSON_LINES:
            return serialized + "\n"
        elif self._config.format == StreamFormat.SSE:
            return f"data: {serialized}\n\n"
        else:
            return serialized

    def close(self) -> None:
        """Close the stream."""
        self._closed = True

    def get_stats(self) -> StreamStats:
        """Get streaming statistics.

        Returns:
            Current statistics.
        """
        return self._stats.model_copy()

    @property
    def content_type(self) -> str:
        """Get appropriate content type.

        Returns:
            Content type header value.
        """
        if self._config.format == StreamFormat.SSE:
            return "text/event-stream"
        elif self._config.format == StreamFormat.JSON_LINES:
            return "application/x-ndjson"
        else:
            return "application/octet-stream"

class SSEStream:
    """Server-Sent Events stream.

    Provides SSE streaming with heartbeat and reconnection support.
    """

    def __init__(
        self,
        heartbeat_interval_ms: int = 15000,
        retry_ms: int = 3000,
    ) -> None:
        """Initialize SSE stream.

        Args:
            heartbeat_interval_ms: Heartbeat interval in milliseconds.
            retry_ms: Client retry interval in milliseconds.
        """
        self._heartbeat_interval = heartbeat_interval_ms / 1000
        self._retry_ms = retry_ms
        self._event_queue: asyncio.Queue[SSEEvent | None] = asyncio.Queue()
        self._stats = StreamStats()
        self._closed = False
        self._event_id = 0

    async def send(
        self,
        data: str | dict[str, Any],
        event: str | None = None,
    ) -> None:
        """Send an SSE event.

        Args:
            data: Event data.
            event: Event type/name.
        """
        if self._closed:
            return

        self._event_id += 1
        sse_event = SSEEvent(
            data=data,
            event=event,
            id=str(self._event_id),
            retry=self._retry_ms if self._event_id == 1 else None,
        )

        await self._event_queue.put(sse_event)
        self._stats.events_sent += 1

    async def close(self) -> None:
        """Close the SSE stream."""
        self._closed = True
        await self._event_queue.put(None)

    async def __aiter__(self) -> AsyncIterator[bytes]:
        """Iterate over SSE events.

        Yields:
            Encoded SSE events.
        """
        self._stats.start_time = datetime.now(UTC)

        while not self._closed:
            try:
                # Wait for event with timeout for heartbeat
                event = await asyncio.wait_for(
                    self._event_queue.get(),
                    timeout=self._heartbeat_interval,
                )

                if event is None:
                    break

                chunk = event.to_string().encode("utf-8")
                self._stats.bytes_sent += len(chunk)
                self._stats.chunks_sent += 1

                yield chunk

            except asyncio.TimeoutError:
                # Send heartbeat comment
                heartbeat = ": heartbeat\n\n".encode("utf-8")
                self._stats.bytes_sent += len(heartbeat)
                yield heartbeat

        end_time = datetime.now(UTC)
        if self._stats.start_time:
            self._stats.duration_ms = (
                end_time - self._stats.start_time
            ).total_seconds() * 1000

    def get_stats(self) -> StreamStats:
        """Get streaming statistics.

        Returns:
            Current statistics.
        """
        return self._stats.model_copy()

    @property
    def content_type(self) -> str:
        """Get content type."""
        return "text/event-stream"

    @property
    def is_closed(self) -> bool:
        """Check if stream is closed."""
        return self._closed

class ChunkedStream[T]:
    """Chunked transfer encoding stream.

    Streams large data in chunks with progress tracking.
    """

    def __init__(
        self,
        source: AsyncIterator[T],
        chunk_size: int = 8192,
        total_size: int | None = None,
    ) -> None:
        """Initialize chunked stream.

        Args:
            source: Async iterator of data.
            chunk_size: Size of chunks.
            total_size: Total size if known (for progress).
        """
        self._source = source
        self._chunk_size = chunk_size
        self._total_size = total_size
        self._stats = StreamStats()
        self._buffer = b""

    async def __aiter__(self) -> AsyncIterator[bytes]:
        """Iterate over chunks.

        Yields:
            Data chunks.
        """
        self._stats.start_time = datetime.now(UTC)

        async for item in self._source:
            # Convert item to bytes
            if isinstance(item, bytes):
                data = item
            elif isinstance(item, str):
                data = item.encode("utf-8")
            else:
                data = json.dumps(item).encode("utf-8")

            self._buffer += data

            # Yield complete chunks
            while len(self._buffer) >= self._chunk_size:
                chunk = self._buffer[:self._chunk_size]
                self._buffer = self._buffer[self._chunk_size:]

                self._stats.bytes_sent += len(chunk)
                self._stats.chunks_sent += 1

                yield chunk

        # Yield remaining buffer
        if self._buffer:
            self._stats.bytes_sent += len(self._buffer)
            self._stats.chunks_sent += 1
            yield self._buffer

        end_time = datetime.now(UTC)
        if self._stats.start_time:
            self._stats.duration_ms = (
                end_time - self._stats.start_time
            ).total_seconds() * 1000

    def get_stats(self) -> StreamStats:
        """Get streaming statistics.

        Returns:
            Current statistics.
        """
        return self._stats.model_copy()

    @property
    def progress(self) -> float | None:
        """Get progress percentage if total size known.

        Returns:
            Progress percentage or None.
        """
        if self._total_size and self._total_size > 0:
            return (self._stats.bytes_sent / self._total_size) * 100
        return None


async def stream_json_array(
    items: AsyncIterator[Any],
    config: StreamConfig | None = None,
) -> AsyncIterator[bytes]:
    """Stream items as a JSON array.

    Streams items as a valid JSON array with proper formatting.
    Useful for streaming large collections.

    Args:
        items: Async iterator of items to stream.
        config: Optional streaming configuration.

    Yields:
        Encoded JSON chunks forming a valid array.
    """
    yield b"["
    first = True

    async for item in items:
        if not first:
            yield b","
        first = False

        if isinstance(item, str):
            yield json.dumps(item).encode("utf-8")
        elif isinstance(item, (dict, list)):
            yield json.dumps(item).encode("utf-8")
        else:
            yield json.dumps(item).encode("utf-8")

    yield b"]"
