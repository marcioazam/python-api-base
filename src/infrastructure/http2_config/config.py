"""http2_config configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING
from .constants import (
    DEFAULT_INITIAL_WINDOW_SIZE,
    DEFAULT_MAX_CONCURRENT_STREAMS,
    DEFAULT_MAX_HEADER_LIST_SIZE,
    MAX_CONCURRENT_STREAMS_LIMIT,
    MAX_FRAME_SIZE,
    MAX_WINDOW_SIZE,
    MIN_FRAME_SIZE,
)
from .enums import HTTPProtocol, PushPriority

if TYPE_CHECKING:
    pass


@dataclass
class MultiplexConfig:
    """HTTP/2 multiplexing configuration."""

    max_concurrent_streams: int = DEFAULT_MAX_CONCURRENT_STREAMS
    initial_window_size: int = DEFAULT_INITIAL_WINDOW_SIZE
    max_frame_size: int = MIN_FRAME_SIZE
    max_header_list_size: int = DEFAULT_MAX_HEADER_LIST_SIZE
    enable_connect_protocol: bool = False

    def validate(self) -> list[str]:
        """Validate configuration values per RFC 7540."""
        errors: list[str] = []
        if self.max_concurrent_streams < 1:
            errors.append("max_concurrent_streams must be >= 1")
        if self.max_concurrent_streams > MAX_CONCURRENT_STREAMS_LIMIT:
            errors.append("max_concurrent_streams exceeds max value")
        if self.initial_window_size < 0:
            errors.append("initial_window_size must be >= 0")
        if self.initial_window_size > MAX_WINDOW_SIZE:
            errors.append("initial_window_size exceeds max value")
        if self.max_frame_size < MIN_FRAME_SIZE:
            errors.append("max_frame_size must be >= 16384")
        if self.max_frame_size > MAX_FRAME_SIZE:
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
    push_resources: list[Any] = field(default_factory=list)  # list[PushResource]
    preload_hints: bool = True
    prioritization_enabled: bool = True

    def add_push_resource(
        self,
        path: str,
        content_type: str,
        priority: PushPriority = PushPriority.NORMAL,
    ) -> None:
        """Add a resource for server push."""
        from .service import PushResource
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
