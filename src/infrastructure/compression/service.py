"""Compression service.

**Feature: code-review-refactoring, Task 17.3: Refactor compression.py**
**Validates: Requirements 5.6**
"""

from dataclasses import dataclass, field

from .compressors import Compressor
from .config import CompressionConfig, CompressionResult
from .enums import CompressionAlgorithm
from .factory import CompressorFactory, select_best_algorithm


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

        if not self.should_compress(content_type, original_size, path):
            return CompressionResult(
                original_size=original_size,
                compressed_size=original_size,
                algorithm=CompressionAlgorithm.IDENTITY,
                data=data,
                was_compressed=False,
            )

        algorithm = select_best_algorithm(accept_encoding, self._config.algorithms)
        if algorithm == CompressionAlgorithm.IDENTITY:
            return CompressionResult(
                original_size=original_size,
                compressed_size=original_size,
                algorithm=CompressionAlgorithm.IDENTITY,
                data=data,
                was_compressed=False,
            )

        compressor = self._get_compressor(algorithm)
        compressed_data = compressor.compress(data)
        compressed_size = len(compressed_data)

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
        return (1.0 - (self.total_compressed_bytes / self.total_original_bytes)) * 100

    @property
    def bytes_saved(self) -> int:
        """Total bytes saved."""
        return self.total_original_bytes - self.total_compressed_bytes
