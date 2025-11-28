"""Compression Middleware for automatic response compression.

This module provides middleware for automatic GZip/Brotli compression
based on content-type and response size.

**Feature: api-architecture-analysis**
**Validates: Requirements 4.4**
"""

import gzip
import zlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol, runtime_checkable


class CompressionAlgorithm(Enum):
    """Supported compression algorithms."""

    GZIP = "gzip"
    DEFLATE = "deflate"
    BROTLI = "br"
    IDENTITY = "identity"  # No compression


@dataclass(frozen=True)
class CompressionConfig:
    """Configuration for compression middleware."""

    min_size: int = 1024  # Minimum size in bytes to compress
    level: int = 6  # Compression level (1-9 for gzip/deflate, 0-11 for brotli)
    algorithms: tuple[CompressionAlgorithm, ...] = (
        CompressionAlgorithm.GZIP,
        CompressionAlgorithm.DEFLATE,
    )
    compressible_types: tuple[str, ...] = (
        "text/",
        "application/json",
        "application/xml",
        "application/javascript",
        "application/x-javascript",
        "image/svg+xml",
    )
    excluded_paths: tuple[str, ...] = ()

    def is_compressible_type(self, content_type: str) -> bool:
        """Check if content type is compressible."""
        if not content_type:
            return False
        content_type_lower = content_type.lower().split(";")[0].strip()
        return any(
            content_type_lower.startswith(ct) for ct in self.compressible_types
        )

    def is_excluded_path(self, path: str) -> bool:
        """Check if path is excluded from compression."""
        return any(path.startswith(excluded) for excluded in self.excluded_paths)


@runtime_checkable
class Compressor(Protocol):
    """Protocol for compression implementations."""

    def compress(self, data: bytes) -> bytes: ...
    def decompress(self, data: bytes) -> bytes: ...
    @property
    def algorithm(self) -> CompressionAlgorithm: ...
    @property
    def encoding(self) -> str: ...


class GzipCompressor:
    """GZip compression implementation."""

    def __init__(self, level: int = 6) -> None:
        self._level = min(max(level, 1), 9)

    def compress(self, data: bytes) -> bytes:
        """Compress data using gzip."""
        return gzip.compress(data, compresslevel=self._level)

    def decompress(self, data: bytes) -> bytes:
        """Decompress gzip data."""
        return gzip.decompress(data)

    @property
    def algorithm(self) -> CompressionAlgorithm:
        return CompressionAlgorithm.GZIP

    @property
    def encoding(self) -> str:
        return "gzip"


class DeflateCompressor:
    """Deflate compression implementation."""

    def __init__(self, level: int = 6) -> None:
        self._level = min(max(level, 1), 9)

    def compress(self, data: bytes) -> bytes:
        """Compress data using deflate."""
        return zlib.compress(data, level=self._level)

    def decompress(self, data: bytes) -> bytes:
        """Decompress deflate data."""
        return zlib.decompress(data)

    @property
    def algorithm(self) -> CompressionAlgorithm:
        return CompressionAlgorithm.DEFLATE

    @property
    def encoding(self) -> str:
        return "deflate"


class IdentityCompressor:
    """No-op compressor (identity encoding)."""

    def compress(self, data: bytes) -> bytes:
        """Return data unchanged."""
        return data

    def decompress(self, data: bytes) -> bytes:
        """Return data unchanged."""
        return data

    @property
    def algorithm(self) -> CompressionAlgorithm:
        return CompressionAlgorithm.IDENTITY

    @property
    def encoding(self) -> str:
        return "identity"


# Optional Brotli support
try:
    import brotli

    class BrotliCompressor:
        """Brotli compression implementation."""

        def __init__(self, level: int = 6) -> None:
            self._level = min(max(level, 0), 11)

        def compress(self, data: bytes) -> bytes:
            """Compress data using brotli."""
            return brotli.compress(data, quality=self._level)

        def decompress(self, data: bytes) -> bytes:
            """Decompress brotli data."""
            return brotli.decompress(data)

        @property
        def algorithm(self) -> CompressionAlgorithm:
            return CompressionAlgorithm.BROTLI

        @property
        def encoding(self) -> str:
            return "br"

    BROTLI_AVAILABLE = True
except ImportError:
    BROTLI_AVAILABLE = False
    BrotliCompressor = None  # type: ignore


@dataclass
class CompressionResult:
    """Result of compression operation."""

    original_size: int
    compressed_size: int
    algorithm: CompressionAlgorithm
    data: bytes
    was_compressed: bool

    @property
    def compression_ratio(self) -> float:
        """Calculate compression ratio."""
        if self.original_size == 0:
            return 0.0
        return 1.0 - (self.compressed_size / self.original_size)

    @property
    def savings_percent(self) -> float:
        """Calculate percentage of bytes saved."""
        return self.compression_ratio * 100


class CompressorFactory:
    """Factory for creating compressors."""

    _compressors: dict[CompressionAlgorithm, type] = {
        CompressionAlgorithm.GZIP: GzipCompressor,
        CompressionAlgorithm.DEFLATE: DeflateCompressor,
        CompressionAlgorithm.IDENTITY: IdentityCompressor,
    }

    @classmethod
    def register(cls, algorithm: CompressionAlgorithm, compressor_class: type) -> None:
        """Register a compressor for an algorithm."""
        cls._compressors[algorithm] = compressor_class

    @classmethod
    def create(cls, algorithm: CompressionAlgorithm, level: int = 6) -> Compressor:
        """Create a compressor for the given algorithm."""
        if algorithm == CompressionAlgorithm.BROTLI:
            if BROTLI_AVAILABLE and BrotliCompressor:
                return BrotliCompressor(level)
            raise ValueError("Brotli compression not available. Install 'brotli' package.")

        compressor_class = cls._compressors.get(algorithm)
        if not compressor_class:
            raise ValueError(f"Unknown compression algorithm: {algorithm}")

        if algorithm == CompressionAlgorithm.IDENTITY:
            return compressor_class()
        return compressor_class(level)

    @classmethod
    def available_algorithms(cls) -> list[CompressionAlgorithm]:
        """Get list of available compression algorithms."""
        algorithms = list(cls._compressors.keys())
        if BROTLI_AVAILABLE:
            algorithms.append(CompressionAlgorithm.BROTLI)
        return algorithms


def parse_accept_encoding(header: str) -> list[tuple[CompressionAlgorithm, float]]:
    """Parse Accept-Encoding header and return algorithms with quality values."""
    if not header:
        return [(CompressionAlgorithm.IDENTITY, 1.0)]

    result: list[tuple[CompressionAlgorithm, float]] = []
    encoding_map = {
        "gzip": CompressionAlgorithm.GZIP,
        "deflate": CompressionAlgorithm.DEFLATE,
        "br": CompressionAlgorithm.BROTLI,
        "identity": CompressionAlgorithm.IDENTITY,
        "*": CompressionAlgorithm.GZIP,  # Default for wildcard
    }

    for part in header.split(","):
        part = part.strip()
        if not part:
            continue

        # Parse encoding and quality
        if ";q=" in part:
            encoding, q_str = part.split(";q=", 1)
            try:
                quality = float(q_str.strip())
            except ValueError:
                quality = 1.0
        else:
            encoding = part
            quality = 1.0

        encoding = encoding.strip().lower()
        if encoding in encoding_map:
            result.append((encoding_map[encoding], quality))

    # Sort by quality (descending)
    result.sort(key=lambda x: x[1], reverse=True)
    return result if result else [(CompressionAlgorithm.IDENTITY, 1.0)]


def select_best_algorithm(
    accept_encoding: str,
    supported: tuple[CompressionAlgorithm, ...],
) -> CompressionAlgorithm:
    """Select the best compression algorithm based on Accept-Encoding header."""
    parsed = parse_accept_encoding(accept_encoding)

    for algorithm, quality in parsed:
        if quality > 0 and algorithm in supported:
            # Check if algorithm is actually available
            if algorithm == CompressionAlgorithm.BROTLI and not BROTLI_AVAILABLE:
                continue
            return algorithm

    return CompressionAlgorithm.IDENTITY



class CompressionService:
    """Service for handling compression operations."""

    def __init__(self, config: CompressionConfig | None = None) -> None:
        self._config = config or CompressionConfig()
        self._compressors: dict[CompressionAlgorithm, Compressor] = {}

    def _get_compressor(self, algorithm: CompressionAlgorithm) -> Compressor:
        """Get or create a compressor for the algorithm."""
        if algorithm not in self._compressors:
            self._compressors[algorithm] = CompressorFactory.create(
                algorithm, self._config.level
            )
        return self._compressors[algorithm]

    def should_compress(
        self,
        content_type: str,
        content_length: int,
        path: str = "",
    ) -> bool:
        """Determine if content should be compressed."""
        if content_length < self._config.min_size:
            return False
        if not self._config.is_compressible_type(content_type):
            return False
        if path and self._config.is_excluded_path(path):
            return False
        return True

    def compress(
        self,
        data: bytes,
        accept_encoding: str = "",
        content_type: str = "",
        path: str = "",
    ) -> CompressionResult:
        """Compress data using the best available algorithm."""
        original_size = len(data)

        # Check if compression should be applied
        if not self.should_compress(content_type, original_size, path):
            return CompressionResult(
                original_size=original_size,
                compressed_size=original_size,
                algorithm=CompressionAlgorithm.IDENTITY,
                data=data,
                was_compressed=False,
            )

        # Select best algorithm
        algorithm = select_best_algorithm(accept_encoding, self._config.algorithms)
        if algorithm == CompressionAlgorithm.IDENTITY:
            return CompressionResult(
                original_size=original_size,
                compressed_size=original_size,
                algorithm=CompressionAlgorithm.IDENTITY,
                data=data,
                was_compressed=False,
            )

        # Compress data
        compressor = self._get_compressor(algorithm)
        compressed_data = compressor.compress(data)
        compressed_size = len(compressed_data)

        # Only use compressed version if it's actually smaller
        if compressed_size >= original_size:
            return CompressionResult(
                original_size=original_size,
                compressed_size=original_size,
                algorithm=CompressionAlgorithm.IDENTITY,
                data=data,
                was_compressed=False,
            )

        return CompressionResult(
            original_size=original_size,
            compressed_size=compressed_size,
            algorithm=algorithm,
            data=compressed_data,
            was_compressed=True,
        )

    def decompress(self, data: bytes, encoding: str) -> bytes:
        """Decompress data based on encoding."""
        encoding_map = {
            "gzip": CompressionAlgorithm.GZIP,
            "deflate": CompressionAlgorithm.DEFLATE,
            "br": CompressionAlgorithm.BROTLI,
            "identity": CompressionAlgorithm.IDENTITY,
        }

        algorithm = encoding_map.get(encoding.lower(), CompressionAlgorithm.IDENTITY)
        if algorithm == CompressionAlgorithm.IDENTITY:
            return data

        compressor = self._get_compressor(algorithm)
        return compressor.decompress(data)


@dataclass
class CompressionStats:
    """Statistics for compression operations."""

    total_requests: int = 0
    compressed_requests: int = 0
    total_original_bytes: int = 0
    total_compressed_bytes: int = 0
    by_algorithm: dict[CompressionAlgorithm, int] = field(default_factory=dict)

    def record(self, result: CompressionResult) -> None:
        """Record a compression result."""
        self.total_requests += 1
        self.total_original_bytes += result.original_size

        if result.was_compressed:
            self.compressed_requests += 1
            self.total_compressed_bytes += result.compressed_size
            self.by_algorithm[result.algorithm] = (
                self.by_algorithm.get(result.algorithm, 0) + 1
            )
        else:
            self.total_compressed_bytes += result.original_size

    @property
    def compression_rate(self) -> float:
        """Percentage of requests that were compressed."""
        if self.total_requests == 0:
            return 0.0
        return (self.compressed_requests / self.total_requests) * 100

    @property
    def overall_savings(self) -> float:
        """Overall bytes saved percentage."""
        if self.total_original_bytes == 0:
            return 0.0
        return (
            1.0 - (self.total_compressed_bytes / self.total_original_bytes)
        ) * 100

    @property
    def bytes_saved(self) -> int:
        """Total bytes saved."""
        return self.total_original_bytes - self.total_compressed_bytes


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
            self._algorithms.insert(0, CompressionAlgorithm.BROTLI)  # Prefer brotli
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


# Convenience functions
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
