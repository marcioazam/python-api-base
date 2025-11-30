"""Compressor implementations.

**Feature: code-review-refactoring, Task 17.3: Refactor compression.py**
**Validates: Requirements 5.6**
"""

import gzip
import zlib
from typing import Protocol, runtime_checkable

from .enums import CompressionAlgorithm


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
        if not 1 <= level <= 9:
            raise ValueError(
                f"Invalid compression level {level}: must be between 1 and 9"
            )
        self._level = level

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
        if not 1 <= level <= 9:
            raise ValueError(
                f"Invalid compression level {level}: must be between 1 and 9"
            )
        self._level = level

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
            if not 0 <= level <= 11:
                raise ValueError(
                    f"Invalid compression level {level}: must be between 0 and 11"
                )
            self._level = level

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
