"""HTTP/2 and HTTP/3 Configuration Module.

Provides configuration and utilities for HTTP/2 and HTTP/3 support
including server push, multiplexing, and protocol negotiation.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class HTTPProtocol(Enum):
    """Supported HTTP protocols."""

    HTTP_1_1 = "http/1.1"
    HTTP_2 = "h2"
    HTTP_3 = "h3"


class PushPriority(Enum):
    """Server push priority levels."""

    HIGHEST = 0
    HIGH = 64
    NORMAL = 128
    LOW = 192
    LOWEST = 255


@dataclass(frozen=True)
class PushResource:
    """Resource to be pushed to client."""

    path: str
    content_type: str
    priority: PushPriority = PushPriority.NORMAL
    headers: dict[str, str] = field(default_factory=dict)

    def to_link_header(self) -> str:
        """Convert to Link header format for preload."""
        rel = "preload"
        as_type = self._get_as_type()
        return f'<{self.path}>; rel={rel}; as={as_type}'

    def _get_as_type(self) -> str:
        """Get 'as' attribute based on content type."""
        type_map = {
            "text/css": "style",
            "application/javascript": "script",
            "text/javascript": "script",
            "image/": "image",
            "font/": "font",
            "application/json": "fetch",
        }
        for prefix, as_type in type_map.items():
            if self.content_type.startswith(prefix):
                return as_type
        return "fetch"


@dataclass
class MultiplexConfig:
    """HTTP/2 multiplexing configuration."""

    max_concurrent_streams: int = 100
    initial_window_size: int = 65535
    max_frame_size: int = 16384
    max_header_list_size: int = 8192
    enable_connect_protocol: bool = False

    def validate(self) -> list[str]:
        """Validate configuration values."""
        errors: list[str] = []
        if self.max_concurrent_streams < 1:
            errors.append("max_concurrent_streams must be >= 1")
        if self.max_concurrent_streams > 2147483647:
            errors.append("max_concurrent_streams exceeds max value")
        if self.initial_window_size < 0:
            errors.append("initial_window_size must be >= 0")
        if self.initial_window_size > 2147483647:
            errors.append("initial_window_size exceeds max value")
        if self.max_frame_size < 16384:
            errors.append("max_frame_size must be >= 16384")
        if self.max_frame_size > 16777215:
            errors.append("max_frame_size exceeds max value")
        if self.max_header_list_size < 0:
            errors.append("max_header_list_size must be >= 0")
        return errors


@dataclass
class HTTP3Config:
    """HTTP/3 (QUIC) specific configuration."""

    max_idle_timeout_ms: int = 30000
    max_udp_payload_size: int = 65527
    initial_max_data: int = 10485760
    initial_max_stream_data_bidi_local: int = 1048576
    initial_max_stream_data_bidi_remote: int = 1048576
    initial_max_stream_data_uni: int = 1048576
    initial_max_streams_bidi: int = 100
    initial_max_streams_uni: int = 100
    disable_active_migration: bool = False

    def validate(self) -> list[str]:
        """Validate HTTP/3 configuration."""
        errors: list[str] = []
        if self.max_idle_timeout_ms < 0:
            errors.append("max_idle_timeout_ms must be >= 0")
        if self.max_udp_payload_size < 1200:
            errors.append("max_udp_payload_size must be >= 1200")
        if self.initial_max_data < 0:
            errors.append("initial_max_data must be >= 0")
        return errors


@dataclass
class HTTP2Config:
    """Complete HTTP/2 configuration."""

    enabled: bool = True
    multiplex: MultiplexConfig = field(default_factory=MultiplexConfig)
    server_push_enabled: bool = True
    push_resources: list[PushResource] = field(default_factory=list)
    preload_hints: bool = True
    prioritization_enabled: bool = True

    def add_push_resource(
        self,
        path: str,
        content_type: str,
        priority: PushPriority = PushPriority.NORMAL,
    ) -> None:
        """Add a resource for server push."""
        resource = PushResource(path=path, content_type=content_type, priority=priority)
        self.push_resources.append(resource)

    def get_link_headers(self) -> list[str]:
        """Get Link headers for all push resources."""
        return [r.to_link_header() for r in self.push_resources]

    def validate(self) -> list[str]:
        """Validate complete configuration."""
        return self.multiplex.validate()


@dataclass
class ProtocolConfig:
    """Combined protocol configuration."""

    http2: HTTP2Config = field(default_factory=HTTP2Config)
    http3: HTTP3Config = field(default_factory=HTTP3Config)
    preferred_protocol: HTTPProtocol = HTTPProtocol.HTTP_2
    fallback_enabled: bool = True
    alpn_protocols: list[str] = field(
        default_factory=lambda: ["h2", "http/1.1"]
    )

    def get_supported_protocols(self) -> list[HTTPProtocol]:
        """Get list of supported protocols."""
        protocols: list[HTTPProtocol] = []
        if self.http2.enabled:
            protocols.append(HTTPProtocol.HTTP_2)
        if "h3" in self.alpn_protocols:
            protocols.append(HTTPProtocol.HTTP_3)
        if self.fallback_enabled:
            protocols.append(HTTPProtocol.HTTP_1_1)
        return protocols

    def validate(self) -> list[str]:
        """Validate all protocol configurations."""
        errors: list[str] = []
        errors.extend(self.http2.validate())
        errors.extend(self.http3.validate())
        if not self.alpn_protocols:
            errors.append("alpn_protocols cannot be empty")
        return errors


class ServerPushManager:
    """Manages HTTP/2 server push resources."""

    def __init__(self, config: HTTP2Config) -> None:
        self._config = config
        self._route_resources: dict[str, list[PushResource]] = {}

    def register_push(
        self,
        route: str,
        resources: list[PushResource],
    ) -> None:
        """Register push resources for a route."""
        self._route_resources[route] = resources

    def get_push_resources(self, route: str) -> list[PushResource]:
        """Get push resources for a route."""
        return self._route_resources.get(route, [])

    def get_link_header(self, route: str) -> str | None:
        """Get combined Link header for route."""
        resources = self.get_push_resources(route)
        if not resources:
            return None
        links = [r.to_link_header() for r in resources]
        return ", ".join(links)

    def should_push(self, route: str) -> bool:
        """Check if route has push resources."""
        return (
            self._config.server_push_enabled
            and route in self._route_resources
            and len(self._route_resources[route]) > 0
        )


class StreamPrioritizer:
    """HTTP/2 stream prioritization manager."""

    def __init__(self) -> None:
        self._stream_weights: dict[int, int] = {}
        self._stream_dependencies: dict[int, int] = {}
        self._exclusive: dict[int, bool] = {}

    def set_priority(
        self,
        stream_id: int,
        weight: int = 16,
        depends_on: int = 0,
        exclusive: bool = False,
    ) -> None:
        """Set stream priority."""
        weight = max(1, min(256, weight))
        self._stream_weights[stream_id] = weight
        self._stream_dependencies[stream_id] = depends_on
        self._exclusive[stream_id] = exclusive

    def get_weight(self, stream_id: int) -> int:
        """Get stream weight (1-256)."""
        return self._stream_weights.get(stream_id, 16)

    def get_dependency(self, stream_id: int) -> int:
        """Get stream dependency."""
        return self._stream_dependencies.get(stream_id, 0)

    def is_exclusive(self, stream_id: int) -> bool:
        """Check if stream has exclusive dependency."""
        return self._exclusive.get(stream_id, False)

    def calculate_effective_weight(self, stream_id: int) -> float:
        """Calculate effective weight considering dependencies."""
        weight = self.get_weight(stream_id)
        dep = self.get_dependency(stream_id)
        if dep == 0:
            return float(weight)
        parent_weight = self.calculate_effective_weight(dep)
        return (weight / 256.0) * parent_weight

    def remove_stream(self, stream_id: int) -> None:
        """Remove stream from prioritization."""
        self._stream_weights.pop(stream_id, None)
        self._stream_dependencies.pop(stream_id, None)
        self._exclusive.pop(stream_id, None)


class FlowController:
    """HTTP/2 flow control manager."""

    def __init__(self, initial_window: int = 65535) -> None:
        self._connection_window = initial_window
        self._stream_windows: dict[int, int] = {}
        self._initial_window = initial_window

    def get_connection_window(self) -> int:
        """Get connection-level window size."""
        return self._connection_window

    def get_stream_window(self, stream_id: int) -> int:
        """Get stream-level window size."""
        return self._stream_windows.get(stream_id, self._initial_window)

    def consume(self, stream_id: int, size: int) -> bool:
        """Consume window for data transmission."""
        if size > self._connection_window:
            return False
        stream_window = self.get_stream_window(stream_id)
        if size > stream_window:
            return False
        self._connection_window -= size
        self._stream_windows[stream_id] = stream_window - size
        return True

    def update_window(self, stream_id: int | None, increment: int) -> None:
        """Update window size (WINDOW_UPDATE frame)."""
        if stream_id is None:
            self._connection_window += increment
        else:
            current = self.get_stream_window(stream_id)
            self._stream_windows[stream_id] = current + increment

    def can_send(self, stream_id: int, size: int) -> bool:
        """Check if data can be sent."""
        if size > self._connection_window:
            return False
        return size <= self.get_stream_window(stream_id)


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


class HTTP2Connection:
    """HTTP/2 connection manager."""

    def __init__(self, config: MultiplexConfig) -> None:
        self._config = config
        self._prioritizer = StreamPrioritizer()
        self._flow_controller = FlowController(config.initial_window_size)
        self._stats = ConnectionStats()
        self._next_stream_id = 1

    @property
    def config(self) -> MultiplexConfig:
        """Get connection configuration."""
        return self._config

    @property
    def stats(self) -> ConnectionStats:
        """Get connection statistics."""
        return self._stats

    @property
    def prioritizer(self) -> StreamPrioritizer:
        """Get stream prioritizer."""
        return self._prioritizer

    @property
    def flow_controller(self) -> FlowController:
        """Get flow controller."""
        return self._flow_controller

    def can_open_stream(self) -> bool:
        """Check if new stream can be opened."""
        return self._stats.active_streams < self._config.max_concurrent_streams

    def open_stream(self, weight: int = 16) -> int | None:
        """Open new stream, returns stream ID or None."""
        if not self.can_open_stream():
            return None
        stream_id = self._next_stream_id
        self._next_stream_id += 2
        self._prioritizer.set_priority(stream_id, weight)
        self._stats.record_stream_open()
        self._stats.last_stream_id = stream_id
        return stream_id

    def close_stream(self, stream_id: int) -> None:
        """Close a stream."""
        self._prioritizer.remove_stream(stream_id)
        self._stats.record_stream_close()

    def send_data(self, stream_id: int, data: bytes) -> bool:
        """Send data on stream."""
        size = len(data)
        if not self._flow_controller.can_send(stream_id, size):
            return False
        self._flow_controller.consume(stream_id, size)
        self._stats.record_frame_sent(size)
        return True


def create_default_config() -> ProtocolConfig:
    """Create default protocol configuration."""
    return ProtocolConfig(
        http2=HTTP2Config(
            enabled=True,
            multiplex=MultiplexConfig(
                max_concurrent_streams=100,
                initial_window_size=65535,
                max_frame_size=16384,
            ),
            server_push_enabled=True,
        ),
        http3=HTTP3Config(),
        preferred_protocol=HTTPProtocol.HTTP_2,
        fallback_enabled=True,
    )


def get_uvicorn_http2_settings(config: HTTP2Config) -> dict[str, Any]:
    """Get Uvicorn settings for HTTP/2."""
    return {
        "http": "h2" if config.enabled else "auto",
        "h2_max_concurrent_streams": config.multiplex.max_concurrent_streams,
        "h2_max_header_list_size": config.multiplex.max_header_list_size,
    }


def get_hypercorn_http2_settings(config: HTTP2Config) -> dict[str, Any]:
    """Get Hypercorn settings for HTTP/2."""
    return {
        "h2_max_concurrent_streams": config.multiplex.max_concurrent_streams,
        "h2_max_header_list_size": config.multiplex.max_header_list_size,
        "h2_max_inbound_frame_size": config.multiplex.max_frame_size,
    }
