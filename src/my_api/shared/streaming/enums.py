"""streaming enums.

**Feature: shared-modules-code-review-fixes, Task 10.1**
**Validates: Requirements 3.4**
"""

from enum import Enum


class StreamFormat(str, Enum):
    """Stream output formats."""

    JSON_LINES = "json_lines"  # Newline-delimited JSON
    SSE = "sse"  # Server-Sent Events
    CHUNKED = "chunked"  # Raw chunked transfer
