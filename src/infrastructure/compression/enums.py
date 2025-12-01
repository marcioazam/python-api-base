"""Compression enums.

**Feature: code-review-refactoring, Task 17.3: Refactor compression.py**
**Validates: Requirements 5.6**
"""

from enum import Enum


class CompressionAlgorithm(Enum):
    """Supported compression algorithms."""

    GZIP = "gzip"
    DEFLATE = "deflate"
    BROTLI = "br"
    IDENTITY = "identity"
