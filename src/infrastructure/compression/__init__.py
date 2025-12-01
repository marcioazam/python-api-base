"""Compression Middleware for automatic response compression.

**Feature: code-review-refactoring, Task 17.3: Refactor compression.py**
**Validates: Requirements 5.6**
"""

from .builder import (
    CompressionConfigBuilder,
    compress_response,
    create_compression_service,
)
from .compressors import (
    BROTLI_AVAILABLE,
    BrotliCompressor,
    Compressor,
    DeflateCompressor,
    GzipCompressor,
    IdentityCompressor,
)
from .config import CompressionConfig, CompressionResult
from .enums import CompressionAlgorithm
from .factory import CompressorFactory, parse_accept_encoding, select_best_algorithm
from .service import CompressionService, CompressionStats

__all__ = [
    "BROTLI_AVAILABLE",
    "BrotliCompressor",
    "CompressionAlgorithm",
    "CompressionConfig",
    "CompressionConfigBuilder",
    "CompressionResult",
    "CompressionService",
    "CompressionStats",
    "Compressor",
    "CompressorFactory",
    "DeflateCompressor",
    "GzipCompressor",
    "IdentityCompressor",
    "compress_response",
    "create_compression_service",
    "parse_accept_encoding",
    "select_best_algorithm",
]
