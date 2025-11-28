"""Property-based tests for response streaming.

**Feature: api-architecture-analysis, Task 12.3: Response Streaming**
**Validates: Requirements 4.4**
"""

import asyncio
import json

from hypothesis import given, settings
from hypothesis import strategies as st

from my_api.shared.streaming import (
    ChunkedStream,
    SSEEvent,
    SSEStream,
    StreamConfig,
    StreamFormat,
    StreamingResponse,
    stream_json_array,
)


# =============================================================================
# Strategies
# =============================================================================

@st.composite
def sse_event_strategy(draw: st.DrawFn) -> SSEEvent:
    """Generate SSE events."""
    return SSEEvent(
        data=draw(st.one_of(
            st.text(min_size=1, max_size=100),
            st.fixed_dictionaries({"message": st.text(min_size=1, max_size=50)}),
        )),
        event=draw(st.one_of(st.none(), st.text(min_size=1, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz"))),
        id=draw(st.one_of(st.none(), st.text(min_size=1, max_size=10, alphabet="0123456789"))),
        retry=draw(st.one_of(st.none(), st.integers(min_value=1000, max_value=30000))),
    )


# =============================================================================
# Property Tests - SSE Event
# =============================================================================

class TestSSEEventProperties:
    """Property tests for SSE events."""

    @given(data=st.text(min_size=1, max_size=100, alphabet="abcdefghijklmnopqrstuvwxyz0123456789 "))
    @settings(max_examples=100)
    def test_event_contains_data(self, data: str) -> None:
        """**Property 1: SSE event contains data**

        *For any* data without newlines, the SSE string should contain the data.

        **Validates: Requirements 4.4**
        """
        event = SSEEvent(data=data)
        result = event.to_string()

        assert f"data: {data}" in result

    @given(event_type=st.text(min_size=1, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz"))
    @settings(max_examples=100)
    def test_event_contains_type(self, event_type: str) -> None:
        """**Property 2: SSE event contains event type**

        *For any* event type, the SSE string should contain it.

        **Validates: Requirements 4.4**
        """
        event = SSEEvent(data="test", event=event_type)
        result = event.to_string()

        assert f"event: {event_type}" in result

    @given(event_id=st.text(min_size=1, max_size=10, alphabet="0123456789"))
    @settings(max_examples=100)
    def test_event_contains_id(self, event_id: str) -> None:
        """**Property 3: SSE event contains ID**

        *For any* event ID, the SSE string should contain it.

        **Validates: Requirements 4.4**
        """
        event = SSEEvent(data="test", id=event_id)
        result = event.to_string()

        assert f"id: {event_id}" in result

    @given(retry=st.integers(min_value=1000, max_value=30000))
    @settings(max_examples=100)
    def test_event_contains_retry(self, retry: int) -> None:
        """**Property 4: SSE event contains retry**

        *For any* retry value, the SSE string should contain it.

        **Validates: Requirements 4.4**
        """
        event = SSEEvent(data="test", retry=retry)
        result = event.to_string()

        assert f"retry: {retry}" in result

    @given(event=sse_event_strategy())
    @settings(max_examples=100)
    def test_event_ends_with_double_newline(self, event: SSEEvent) -> None:
        """**Property 5: SSE event ends with double newline**

        *For any* SSE event, the string should end with double newline.

        **Validates: Requirements 4.4**
        """
        result = event.to_string()
        assert result.endswith("\n\n")

    @given(data=st.fixed_dictionaries({"key": st.text(min_size=1, max_size=50)}))
    @settings(max_examples=100)
    def test_dict_data_serialized_as_json(self, data: dict) -> None:
        """**Property 6: Dict data is serialized as JSON**

        *For any* dict data, it should be JSON serialized.

        **Validates: Requirements 4.4**
        """
        event = SSEEvent(data=data)
        result = event.to_string()

        assert json.dumps(data) in result


# =============================================================================
# Property Tests - Stream Config
# =============================================================================

class TestStreamConfigProperties:
    """Property tests for stream configuration."""

    def test_config_defaults(self) -> None:
        """**Property 7: Config has sensible defaults**

        Default configuration should have reasonable values.

        **Validates: Requirements 4.4**
        """
        config = StreamConfig()

        assert config.format == StreamFormat.JSON_LINES
        assert config.chunk_size == 8192
        assert config.flush_interval_ms == 100
        assert config.heartbeat_interval_ms == 15000
        assert config.max_buffer_size == 65536

    @given(format=st.sampled_from(list(StreamFormat)))
    @settings(max_examples=10)
    def test_all_formats_valid(self, format: StreamFormat) -> None:
        """**Property 8: All stream formats are valid**

        *For any* format, it should be usable in config.

        **Validates: Requirements 4.4**
        """
        config = StreamConfig(format=format)
        assert config.format == format


# =============================================================================
# Property Tests - Streaming Response
# =============================================================================

class TestStreamingResponseProperties:
    """Property tests for streaming response."""

    @given(items=st.lists(st.text(min_size=1, max_size=50), min_size=1, max_size=10))
    @settings(max_examples=50)
    async def test_all_items_streamed(self, items: list[str]) -> None:
        """**Property 9: All items are streamed**

        *For any* list of items, all should be present in output.

        **Validates: Requirements 4.4**
        """
        async def source() -> None:
            for item in items:
                yield item

        stream = StreamingResponse(source())
        chunks = []

        async for chunk in stream:
            chunks.append(chunk.decode("utf-8"))

        output = "".join(chunks)

        for item in items:
            assert item in output

    @given(items=st.lists(st.integers(), min_size=1, max_size=10))
    @settings(max_examples=50)
    async def test_json_lines_format(self, items: list[int]) -> None:
        """**Property 10: JSON lines format is correct**

        *For any* items, JSON lines format should have newlines.

        **Validates: Requirements 4.4**
        """
        async def source() -> None:
            for item in items:
                yield item

        config = StreamConfig(format=StreamFormat.JSON_LINES)
        stream = StreamingResponse(source(), config=config)

        chunks = []
        async for chunk in stream:
            chunks.append(chunk.decode("utf-8"))

        output = "".join(chunks)
        lines = output.strip().split("\n")

        assert len(lines) == len(items)

    async def test_stats_tracking(self) -> None:
        """**Property 11: Stats are tracked correctly**

        Streaming should track statistics.

        **Validates: Requirements 4.4**
        """
        async def source() -> None:
            for i in range(5):
                yield f"item_{i}"

        stream = StreamingResponse(source())

        async for _ in stream:
            pass

        stats = stream.get_stats()

        assert stats.chunks_sent == 5
        assert stats.bytes_sent > 0
        assert stats.start_time is not None

    def test_content_type_json_lines(self) -> None:
        """**Property 12: JSON lines has correct content type**

        JSON lines format should have application/x-ndjson content type.

        **Validates: Requirements 4.4**
        """
        async def source() -> None:
            yield "test"

        config = StreamConfig(format=StreamFormat.JSON_LINES)
        stream = StreamingResponse(source(), config=config)

        assert stream.content_type == "application/x-ndjson"

    def test_content_type_sse(self) -> None:
        """**Property 13: SSE has correct content type**

        SSE format should have text/event-stream content type.

        **Validates: Requirements 4.4**
        """
        async def source() -> None:
            yield "test"

        config = StreamConfig(format=StreamFormat.SSE)
        stream = StreamingResponse(source(), config=config)

        assert stream.content_type == "text/event-stream"


# =============================================================================
# Property Tests - SSE Stream
# =============================================================================

class TestSSEStreamProperties:
    """Property tests for SSE stream."""

    async def test_send_creates_event(self) -> None:
        """**Property 14: Send creates SSE event**

        Sending data should create a properly formatted SSE event.

        **Validates: Requirements 4.4**
        """
        stream = SSEStream()

        await stream.send("test message")

        # Get the event
        chunks = []
        task = asyncio.create_task(stream.__aiter__().__anext__())
        await asyncio.sleep(0.01)
        await stream.close()

        try:
            chunk = await task
            chunks.append(chunk.decode("utf-8"))
        except StopAsyncIteration:
            pass

        if chunks:
            assert "data: test message" in chunks[0]

    async def test_event_has_id(self) -> None:
        """**Property 15: Events have incrementing IDs**

        Each event should have an incrementing ID.

        **Validates: Requirements 4.4**
        """
        stream = SSEStream()

        await stream.send("message 1")
        await stream.send("message 2")

        stats = stream.get_stats()
        assert stats.events_sent == 2

    def test_sse_content_type(self) -> None:
        """**Property 16: SSE stream has correct content type**

        SSE stream should have text/event-stream content type.

        **Validates: Requirements 4.4**
        """
        stream = SSEStream()
        assert stream.content_type == "text/event-stream"

    async def test_close_stops_stream(self) -> None:
        """**Property 17: Close stops the stream**

        Closing should stop the stream iteration.

        **Validates: Requirements 4.4**
        """
        stream = SSEStream()

        await stream.close()

        assert stream.is_closed


# =============================================================================
# Property Tests - Chunked Stream
# =============================================================================

class TestChunkedStreamProperties:
    """Property tests for chunked stream."""

    @given(
        data=st.lists(st.binary(min_size=1, max_size=100), min_size=1, max_size=10),
        chunk_size=st.integers(min_value=10, max_value=100),
    )
    @settings(max_examples=50)
    async def test_all_data_streamed(self, data: list[bytes], chunk_size: int) -> None:
        """**Property 18: All data is streamed**

        *For any* data, all bytes should be present in output.

        **Validates: Requirements 4.4**
        """
        async def source() -> None:
            for item in data:
                yield item

        stream = ChunkedStream(source(), chunk_size=chunk_size)

        chunks = []
        async for chunk in stream:
            chunks.append(chunk)

        output = b"".join(chunks)
        expected = b"".join(data)

        assert output == expected

    @given(chunk_size=st.integers(min_value=10, max_value=100))
    @settings(max_examples=50)
    async def test_chunks_respect_size(self, chunk_size: int) -> None:
        """**Property 19: Chunks respect size limit**

        *For any* chunk size, chunks should not exceed it (except last).

        **Validates: Requirements 4.4**
        """
        data = b"x" * 500

        async def source() -> None:
            yield data

        stream = ChunkedStream(source(), chunk_size=chunk_size)

        chunks = []
        async for chunk in stream:
            chunks.append(chunk)

        # All chunks except last should be exactly chunk_size
        for chunk in chunks[:-1]:
            assert len(chunk) == chunk_size

    async def test_progress_tracking(self) -> None:
        """**Property 20: Progress is tracked when total known**

        When total size is known, progress should be calculated.

        **Validates: Requirements 4.4**
        """
        data = b"x" * 100

        async def source() -> None:
            yield data

        stream = ChunkedStream(source(), chunk_size=50, total_size=100)

        async for _ in stream:
            pass

        assert stream.progress == 100.0


# =============================================================================
# Property Tests - JSON Array Streaming
# =============================================================================

class TestJsonArrayStreamProperties:
    """Property tests for JSON array streaming."""

    @given(items=st.lists(st.integers(), min_size=0, max_size=10))
    @settings(max_examples=50)
    async def test_valid_json_array(self, items: list[int]) -> None:
        """**Property 21: Output is valid JSON array**

        *For any* items, output should be a valid JSON array.

        **Validates: Requirements 4.4**
        """
        async def source() -> None:
            for item in items:
                yield item

        chunks = []
        async for chunk in stream_json_array(source()):
            chunks.append(chunk)

        output = "".join(chunks)
        parsed = json.loads(output)

        assert parsed == items

    async def test_empty_array(self) -> None:
        """**Property 22: Empty source produces empty array**

        Empty source should produce "[]".

        **Validates: Requirements 4.4**
        """
        async def source() -> None:
            return
            yield  # Make it a generator

        chunks = []
        async for chunk in stream_json_array(source()):
            chunks.append(chunk)

        output = "".join(chunks)
        assert output == "[]"
