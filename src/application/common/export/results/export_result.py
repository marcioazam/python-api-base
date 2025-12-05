"""Export result dataclass.

**Feature: application-layer-code-review-2025**
**Refactored: Split from data_export.py for one-class-per-file compliance**
"""

from dataclasses import dataclass, field
from typing import Any

from application.common.export.formats.export_format import ExportFormat


@dataclass
class ExportResult:
    """Export operation result."""

    format: ExportFormat
    record_count: int
    file_size_bytes: int
    duration_ms: float
    checksum: str
    metadata: dict[str, Any] = field(default_factory=dict)
