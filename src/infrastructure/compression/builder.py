"""Compression configuration builder.

**Feature: code-review-refactoring, Task 17.3: Refactor compression.py**
**Validates: Requirements 5.6**
"""

from .compressors import BROTLI_AVAILABLE
from .config import CompressionConfig
from .enums import CompressionAlgorithm
from .service import CompressionService


class CompressionConfigBuilder:
    """Builder for CompressionConfig."""

    def __init__(self) -> None:
        self._min_size = 1024
        self._level = 6
        self._algorithms: list[CompressionAlgorithm] = [
            CompressionAlgorithm.GZIP,
            CompressionAlgorithm.DEFLATE,
        ]
        self._compressible_types: list[str] = [
            "text/",
            "application/json",
            "application/xml",
            "application/javascript",
        ]
        self._excluded_paths: list[str] = []

    def min_size(self, size: int) -> "CompressionConfigBuilder":
        """Set minimum size for compression."""
        self._min_size = max(0, size)
        return self

    def level(self, level: int) -> "CompressionConfigBuilder":
        """Set compression level."""
        self._level = min(max(level, 1), 11)
        return self

    def with_gzip(self) -> "CompressionConfigBuilder":
        """Enable gzip compression."""
        if CompressionAlgorithm.GZIP not in self._algorithms:
            self._algorithms.append(CompressionAlgorithm.GZIP)
        return self

    def with_deflate(self) -> "CompressionConfigBuilder":
        """Enable deflate compression."""
        if CompressionAlgorithm.DEFLATE not in self._algorithms:
            self._algorithms.append(CompressionAlgorithm.DEFLATE)
        return self

    def with_brotli(self) -> "CompressionConfigBuilder":
        """Enable brotli compression."""
        if not BROTLI_AVAILABLE:
            raise ValueError("Brotli not available. Install 'brotli' package.")
        if CompressionAlgorithm.BROTLI not in self._algorithms:
            self._algorithms.insert(0, CompressionAlgorithm.BROTLI)
        return self

    def only_gzip(self) -> "CompressionConfigBuilder":
        """Use only gzip compression."""
        self._algorithms = [CompressionAlgorithm.GZIP]
        return self

    def add_compressible_type(self, content_type: str) -> "CompressionConfigBuilder":
        """Add a compressible content type."""
        if content_type not in self._compressible_types:
            self._compressible_types.append(content_type)
        return self

    def exclude_path(self, path: str) -> "CompressionConfigBuilder":
        """Exclude a path from compression."""
        if path not in self._excluded_paths:
            self._excluded_paths.append(path)
        return self

    def build(self) -> CompressionConfig:
        """Build the configuration."""
        return CompressionConfig(
            min_size=self._min_size,
            level=self._level,
            algorithms=tuple(self._algorithms),
            compressible_types=tuple(self._compressible_types),
            excluded_paths=tuple(self._excluded_paths),
        )


def create_compression_service(
    min_size: int = 1024,
    level: int = 6,
    enable_brotli: bool = False,
) -> CompressionService:
    """Create a compression service with common defaults."""
    builder = CompressionConfigBuilder().min_size(min_size).level(level)
    if enable_brotli and BROTLI_AVAILABLE:
        builder.with_brotli()
    return CompressionService(builder.build())


def compress_response(
    data: bytes,
    accept_encoding: str,
    content_type: str = "application/json",
) -> tuple[bytes, str]:
    """Compress response data and return (data, encoding) tuple."""
    service = CompressionService()
    result = service.compress(data, accept_encoding, content_type)
    return result.data, result.algorithm.value if result.was_compressed else "identity"
