"""http2_config service."""

from dataclasses import dataclass, field
from typing import Any
from .enums import HTTPProtocol, PushPriority
from .models import ConnectionStats
from .config import MultiplexConfig, HTTP3Config, HTTP2Config, ProtocolConfig


@dataclass(frozen=True, slots=True)
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
