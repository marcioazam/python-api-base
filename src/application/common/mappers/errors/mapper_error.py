"""Mapper error exception.

**Feature: application-layer-code-review-2025**
**Refactored: Split from mapper.py for one-class-per-file compliance**
"""

from typing import Any


class MapperError(Exception):
    """Error during mapping operation."""

    def __init__(
        self,
        message: str,
        source_type: str | None = None,
        target_type: str | None = None,
        field: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        self.source_type = source_type
        self.target_type = target_type
        self.field = field
        self.context = context or {}
        super().__init__(message)
