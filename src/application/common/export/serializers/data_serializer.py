"""Data serializer protocol.

**Feature: application-layer-code-review-2025**
**Refactored: Split from data_export.py for one-class-per-file compliance**
"""

from typing import Any, Protocol


class DataSerializer[T](Protocol):
    """Protocol for data serialization."""

    def to_dict(self, obj: T) -> dict[str, Any]: ...
    def from_dict(self, data: dict[str, Any]) -> T: ...
