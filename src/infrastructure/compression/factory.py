"""Compressor factory.

**Feature: code-review-refactoring, Task 17.3: Refactor compression.py**
**Validates: Requirements 5.6**
"""

from .compressors import (
    BROTLI_AVAILABLE,
    BrotliCompressor,
    Compressor,
    DeflateCompressor,
    GzipCompressor,
    IdentityCompressor,
)
from .enums import CompressionAlgorithm


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
        "*": CompressionAlgorithm.GZIP,
    }

    for part in header.split(","):
        part = part.strip()
        if not part:
            continue

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
            if algorithm == CompressionAlgorithm.BROTLI and not BROTLI_AVAILABLE:
                continue
            return algorithm

    return CompressionAlgorithm.IDENTITY
