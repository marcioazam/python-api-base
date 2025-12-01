"""Property-based tests for HTTP/2 and HTTP/3 configuration.

**Feature: api-architecture-analysis, Property 14.2: HTTP/2 and HTTP/3 Support**
**Validates: Requirements 4.4**
"""

import pytest
from hypothesis import given, strategies as st, assume, settings

from my_app.shared.http2_config import (
    HTTPProtocol,
    PushPriority,
    PushResource,
    MultiplexConfig,
    HTTP3Config,
    HTTP2Config,
    ProtocolConfig,
    ServerPushManager,
    StreamPrioritizer,
    FlowController,
    ConnectionStats,
    HTTP2Connection,
    create_default_config,
    get_uvicorn_http2_settings,
    get_hypercorn_http2_settings,
)


# Strategies
content_types = st.sampled_from([
    "text/css",
    "application/javascript",
    "text/javascript",
    "image/png",
    "image/jpeg",
    "font/woff2",
    "application/json",
    "text/html",
])

paths = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="/-_."),
    min_size=1,
    max_size=100,
).map(lambda s: "/" + s.lstrip("/"))

push_priorities = st.sampled_from(list(PushPriority))

push_resources = st.builds(
    PushResource,
    path=paths,
    content_type=content_types,
    priority=push_priorities,
)

valid_max_concurrent = st.integers(min_value=1, max_value=1000)
valid_window_size = st.integers(min_value=0, max_value=2147483647)
valid_frame_size = st.integers(min_value=16384, max_value=16777215)
valid_header_size = st.integers(min_value=0, max_value=65535)

multiplex_configs = st.builds(
    MultiplexConfig,
    max_concurrent_streams=valid_max_concurrent,
    initial_window_size=valid_window_size,
    max_frame_size=valid_frame_size,
    max_header_list_size=valid_header_size,
    enable_connect_protocol=st.booleans(),
)

stream_ids = st.integers(min_value=1, max_value=10000)
weights = st.integers(min_value=1, max_value=256)
data_sizes = st.integers(min_value=1, max_value=10000)


class TestPushResource:
    """Property tests for PushResource."""

    @given(path=paths, content_type=content_types, priority=push_priorities)
    @settings(max_examples=50)
    def test_link_header_contains_path(
        self, path: str, content_type: str, priority: PushPriority
    ) -> None:
        """Link header always contains the resource path."""
        resource = PushResource(path=path, content_type=content_type, priority=priority)
        header = resource.to_link_header()
        assert path in header

    @given(resource=push_resources)
    @settings(max_examples=100)
    def test_link_header_format(self, resource: PushResource) -> None:
        """Link header follows correct format."""
        header = resource.to_link_header()
        assert header.startswith("<")
        assert ">; rel=preload; as=" in header

    @given(path=paths)
    @settings(max_examples=100)
    def test_css_as_type(self, path: str) -> None:
        """CSS content type maps to 'style' as type."""
        resource = PushResource(path=path, content_type="text/css")
        header = resource.to_link_header()
        assert "as=style" in header

    @given(path=paths)
    @settings(max_examples=100)
    def test_js_as_type(self, path: str) -> None:
        """JavaScript content type maps to 'script' as type."""
        resource = PushResource(path=path, content_type="application/javascript")
        header = resource.to_link_header()
        assert "as=script" in header


class TestMultiplexConfig:
    """Property tests for MultiplexConfig."""

    @given(config=multiplex_configs)
    @settings(max_examples=100)
    def test_valid_config_no_errors(self, config: MultiplexConfig) -> None:
        """Valid configuration produces no validation errors."""
        errors = config.validate()
        assert len(errors) == 0

    @given(
        max_concurrent=st.integers(max_value=0),
        window_size=valid_window_size,
        frame_size=valid_frame_size,
    )
    @settings(max_examples=50)
    def test_invalid_concurrent_streams(
        self, max_concurrent: int, window_size: int, frame_size: int
    ) -> None:
        """Invalid max_concurrent_streams produces error."""
        config = MultiplexConfig(
            max_concurrent_streams=max_concurrent,
            initial_window_size=window_size,
            max_frame_size=frame_size,
        )
        errors = config.validate()
        assert any("max_concurrent_streams" in e for e in errors)

    @given(frame_size=st.integers(min_value=0, max_value=16383))
    @settings(max_examples=50)
    def test_invalid_frame_size(self, frame_size: int) -> None:
        """Frame size below minimum produces error."""
        config = MultiplexConfig(max_frame_size=frame_size)
        errors = config.validate()
        assert any("max_frame_size" in e for e in errors)


class TestHTTP3Config:
    """Property tests for HTTP3Config."""

    @given(timeout=st.integers(min_value=0, max_value=60000))
    @settings(max_examples=100)
    def test_valid_timeout(self, timeout: int) -> None:
        """Valid timeout produces no errors."""
        config = HTTP3Config(max_idle_timeout_ms=timeout)
        errors = config.validate()
        assert not any("timeout" in e for e in errors)

    @given(timeout=st.integers(max_value=-1))
    @settings(max_examples=50)
    def test_negative_timeout_error(self, timeout: int) -> None:
        """Negative timeout produces error."""
        config = HTTP3Config(max_idle_timeout_ms=timeout)
        errors = config.validate()
        assert any("timeout" in e for e in errors)


class TestHTTP2Config:
    """Property tests for HTTP2Config."""

    @given(resources=st.lists(push_resources, max_size=10))
    @settings(max_examples=100)
    def test_link_headers_count(self, resources: list[PushResource]) -> None:
        """Link headers count matches resources count."""
        config = HTTP2Config(push_resources=resources)
        headers = config.get_link_headers()
        assert len(headers) == len(resources)

    @given(
        path=paths,
        content_type=content_types,
        priority=push_priorities,
    )
    @settings(max_examples=100)
    def test_add_push_resource(
        self, path: str, content_type: str, priority: PushPriority
    ) -> None:
        """Adding push resource increases count."""
        config = HTTP2Config()
        initial_count = len(config.push_resources)
        config.add_push_resource(path, content_type, priority)
        assert len(config.push_resources) == initial_count + 1


class TestProtocolConfig:
    """Property tests for ProtocolConfig."""

    @given(http2_enabled=st.booleans(), fallback=st.booleans())
    @settings(max_examples=100)
    def test_supported_protocols(self, http2_enabled: bool, fallback: bool) -> None:
        """Supported protocols reflect configuration."""
        config = ProtocolConfig(
            http2=HTTP2Config(enabled=http2_enabled),
            fallback_enabled=fallback,
        )
        protocols = config.get_supported_protocols()
        if http2_enabled:
            assert HTTPProtocol.HTTP_2 in protocols
        if fallback:
            assert HTTPProtocol.HTTP_1_1 in protocols

    def test_default_config_valid(self) -> None:
        """Default configuration is valid."""
        config = create_default_config()
        errors = config.validate()
        assert len(errors) == 0


class TestServerPushManager:
    """Property tests for ServerPushManager."""

    @given(route=paths, resources=st.lists(push_resources, min_size=1, max_size=5))
    @settings(max_examples=100)
    def test_register_and_retrieve(
        self, route: str, resources: list[PushResource]
    ) -> None:
        """Registered resources can be retrieved."""
        config = HTTP2Config(server_push_enabled=True)
        manager = ServerPushManager(config)
        manager.register_push(route, resources)
        retrieved = manager.get_push_resources(route)
        assert retrieved == resources

    @given(route=paths, resources=st.lists(push_resources, min_size=1, max_size=5))
    @settings(max_examples=100)
    def test_should_push_with_resources(
        self, route: str, resources: list[PushResource]
    ) -> None:
        """should_push returns True when resources registered."""
        config = HTTP2Config(server_push_enabled=True)
        manager = ServerPushManager(config)
        manager.register_push(route, resources)
        assert manager.should_push(route) is True

    @given(route=paths)
    @settings(max_examples=100)
    def test_should_push_without_resources(self, route: str) -> None:
        """should_push returns False when no resources."""
        config = HTTP2Config(server_push_enabled=True)
        manager = ServerPushManager(config)
        assert manager.should_push(route) is False

    @given(route=paths, resources=st.lists(push_resources, min_size=1, max_size=5))
    @settings(max_examples=100)
    def test_link_header_not_none(
        self, route: str, resources: list[PushResource]
    ) -> None:
        """Link header is not None when resources exist."""
        config = HTTP2Config(server_push_enabled=True)
        manager = ServerPushManager(config)
        manager.register_push(route, resources)
        header = manager.get_link_header(route)
        assert header is not None


class TestStreamPrioritizer:
    """Property tests for StreamPrioritizer."""

    @given(stream_id=stream_ids, weight=weights)
    @settings(max_examples=100)
    def test_set_and_get_weight(self, stream_id: int, weight: int) -> None:
        """Set weight can be retrieved."""
        prioritizer = StreamPrioritizer()
        prioritizer.set_priority(stream_id, weight)
        assert prioritizer.get_weight(stream_id) == weight

    @given(stream_id=stream_ids, weight=st.integers(min_value=257, max_value=1000))
    @settings(max_examples=50)
    def test_weight_clamped_high(self, stream_id: int, weight: int) -> None:
        """Weight above 256 is clamped."""
        prioritizer = StreamPrioritizer()
        prioritizer.set_priority(stream_id, weight)
        assert prioritizer.get_weight(stream_id) == 256

    @given(stream_id=stream_ids, weight=st.integers(max_value=0))
    @settings(max_examples=50)
    def test_weight_clamped_low(self, stream_id: int, weight: int) -> None:
        """Weight below 1 is clamped."""
        prioritizer = StreamPrioritizer()
        prioritizer.set_priority(stream_id, weight)
        assert prioritizer.get_weight(stream_id) == 1

    @given(stream_id=stream_ids)
    @settings(max_examples=100)
    def test_default_weight(self, stream_id: int) -> None:
        """Default weight is 16."""
        prioritizer = StreamPrioritizer()
        assert prioritizer.get_weight(stream_id) == 16

    @given(stream_id=stream_ids, depends_on=stream_ids)
    @settings(max_examples=100)
    def test_dependency(self, stream_id: int, depends_on: int) -> None:
        """Dependency can be set and retrieved."""
        assume(stream_id != depends_on)
        prioritizer = StreamPrioritizer()
        prioritizer.set_priority(stream_id, depends_on=depends_on)
        assert prioritizer.get_dependency(stream_id) == depends_on

    @given(stream_id=stream_ids, weight=weights)
    @settings(max_examples=100)
    def test_remove_stream(self, stream_id: int, weight: int) -> None:
        """Removed stream returns default values."""
        prioritizer = StreamPrioritizer()
        prioritizer.set_priority(stream_id, weight)
        prioritizer.remove_stream(stream_id)
        assert prioritizer.get_weight(stream_id) == 16


class TestFlowController:
    """Property tests for FlowController."""

    @given(initial=st.integers(min_value=1000, max_value=100000))
    @settings(max_examples=100)
    def test_initial_window(self, initial: int) -> None:
        """Initial window is set correctly."""
        controller = FlowController(initial)
        assert controller.get_connection_window() == initial

    @given(
        initial=st.integers(min_value=1000, max_value=100000),
        stream_id=stream_ids,
        size=st.integers(min_value=1, max_value=500),
    )
    @settings(max_examples=100)
    def test_consume_reduces_window(
        self, initial: int, stream_id: int, size: int
    ) -> None:
        """Consuming reduces window size."""
        assume(size <= initial)
        controller = FlowController(initial)
        controller.consume(stream_id, size)
        assert controller.get_connection_window() == initial - size

    @given(
        initial=st.integers(min_value=100, max_value=1000),
        size=st.integers(min_value=1001, max_value=2000),
    )
    @settings(max_examples=50)
    def test_consume_fails_insufficient_window(self, initial: int, size: int) -> None:
        """Consume fails when window insufficient."""
        controller = FlowController(initial)
        result = controller.consume(1, size)
        assert result is False

    @given(
        initial=st.integers(min_value=1000, max_value=10000),
        increment=st.integers(min_value=1, max_value=1000),
    )
    @settings(max_examples=100)
    def test_update_window(self, initial: int, increment: int) -> None:
        """Window update increases window."""
        controller = FlowController(initial)
        controller.update_window(None, increment)
        assert controller.get_connection_window() == initial + increment


class TestConnectionStats:
    """Property tests for ConnectionStats."""

    @given(opens=st.integers(min_value=0, max_value=100))
    @settings(max_examples=100)
    def test_stream_open_count(self, opens: int) -> None:
        """Stream open count is accurate."""
        stats = ConnectionStats()
        for _ in range(opens):
            stats.record_stream_open()
        assert stats.streams_opened == opens

    @given(
        opens=st.integers(min_value=5, max_value=100),
        closes=st.integers(min_value=0, max_value=5),
    )
    @settings(max_examples=100)
    def test_active_streams(self, opens: int, closes: int) -> None:
        """Active streams = opened - closed."""
        stats = ConnectionStats()
        for _ in range(opens):
            stats.record_stream_open()
        for _ in range(closes):
            stats.record_stream_close()
        assert stats.active_streams == opens - closes

    @given(sizes=st.lists(st.integers(min_value=1, max_value=1000), max_size=20))
    @settings(max_examples=100)
    def test_bytes_sent(self, sizes: list[int]) -> None:
        """Bytes sent is sum of frame sizes."""
        stats = ConnectionStats()
        for size in sizes:
            stats.record_frame_sent(size)
        assert stats.bytes_sent == sum(sizes)
        assert stats.frames_sent == len(sizes)


class TestHTTP2Connection:
    """Property tests for HTTP2Connection."""

    @given(max_streams=st.integers(min_value=1, max_value=100))
    @settings(max_examples=100)
    def test_can_open_stream_initially(self, max_streams: int) -> None:
        """Can open stream when under limit."""
        config = MultiplexConfig(max_concurrent_streams=max_streams)
        conn = HTTP2Connection(config)
        assert conn.can_open_stream() is True

    @given(max_streams=st.integers(min_value=1, max_value=10))
    @settings(max_examples=50)
    def test_cannot_exceed_max_streams(self, max_streams: int) -> None:
        """Cannot open more than max streams."""
        config = MultiplexConfig(max_concurrent_streams=max_streams)
        conn = HTTP2Connection(config)
        for _ in range(max_streams):
            stream_id = conn.open_stream()
            assert stream_id is not None
        assert conn.can_open_stream() is False
        assert conn.open_stream() is None

    @given(weight=weights)
    @settings(max_examples=100)
    def test_open_stream_with_weight(self, weight: int) -> None:
        """Stream opened with specified weight."""
        config = MultiplexConfig()
        conn = HTTP2Connection(config)
        stream_id = conn.open_stream(weight)
        assert stream_id is not None
        assert conn.prioritizer.get_weight(stream_id) == weight

    @given(num_streams=st.integers(min_value=1, max_value=10))
    @settings(max_examples=100)
    def test_stream_ids_increment(self, num_streams: int) -> None:
        """Stream IDs increment by 2 (odd numbers for client)."""
        config = MultiplexConfig(max_concurrent_streams=100)
        conn = HTTP2Connection(config)
        ids = []
        for _ in range(num_streams):
            stream_id = conn.open_stream()
            if stream_id:
                ids.append(stream_id)
        for i in range(1, len(ids)):
            assert ids[i] == ids[i - 1] + 2


class TestUvicornSettings:
    """Property tests for Uvicorn settings generation."""

    @given(enabled=st.booleans(), max_streams=valid_max_concurrent)
    @settings(max_examples=100)
    def test_uvicorn_settings(self, enabled: bool, max_streams: int) -> None:
        """Uvicorn settings reflect configuration."""
        config = HTTP2Config(
            enabled=enabled,
            multiplex=MultiplexConfig(max_concurrent_streams=max_streams),
        )
        settings = get_uvicorn_http2_settings(config)
        expected_http = "h2" if enabled else "auto"
        assert settings["http"] == expected_http
        assert settings["h2_max_concurrent_streams"] == max_streams


class TestHypercornSettings:
    """Property tests for Hypercorn settings generation."""

    @given(max_streams=valid_max_concurrent, frame_size=valid_frame_size)
    @settings(max_examples=100)
    def test_hypercorn_settings(self, max_streams: int, frame_size: int) -> None:
        """Hypercorn settings reflect configuration."""
        config = HTTP2Config(
            multiplex=MultiplexConfig(
                max_concurrent_streams=max_streams,
                max_frame_size=frame_size,
            )
        )
        settings = get_hypercorn_http2_settings(config)
        assert settings["h2_max_concurrent_streams"] == max_streams
        assert settings["h2_max_inbound_frame_size"] == frame_size
