"""Cache serialization utilities.

**Feature: python-api-base-2025-state-of-art**
**Refactored: 2025 - Extracted from providers.py for SRP compliance**
"""

import json
from typing import Protocol, runtime_checkable


@runtime_checkable
class Serializer[T](Protocol):
    """Protocol for type-safe serialization."""

    def serialize(self, value: T) -> bytes:
        """Serialize value to bytes."""
        ...

    def deserialize(self, data: bytes) -> T:
        """Deserialize bytes to value."""
        ...


class JsonSerializer[T]:
    """JSON serializer implementation."""

    def serialize(self, value: T) -> bytes:
        """Serialize value to JSON bytes."""
        return json.dumps(value, default=str).encode("utf-8")

    def deserialize(self, data: bytes) -> T:
        """Deserialize JSON bytes to value."""
        return json.loads(data.decode("utf-8"))
