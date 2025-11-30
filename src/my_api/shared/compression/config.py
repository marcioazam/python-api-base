"""Compression configuration.

**Feature: code-review-refactoring, Task 17.3: Refactor compression.py**
**Validates: Requirements 5.6**
"""

from dataclasses import dataclass

from .enums import CompressionAlgorithm


@dataclass(frozen=True, slots=True)
class CompressionConfig:
    """Configuration for compression middleware."""

    min_size: int = 1024
    level: int = 6
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
        return any(content_type_lower.startswith(ct) for ct in self.compressible_types)

    def is_excluded_path(self, path: str) -> bool:
        """Check if path is excluded from compression."""
        return any(path.startswith(excluded) for excluded in self.excluded_paths)


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
