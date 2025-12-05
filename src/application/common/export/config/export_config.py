"""Export configuration dataclass.

**Feature: application-layer-code-review-2025**
**Refactored: Split from data_export.py for one-class-per-file compliance**
"""

from dataclasses import dataclass

from application.common.export.formats.export_format import ExportFormat


@dataclass
class ExportConfig:
    """Export configuration."""

    format: ExportFormat = ExportFormat.JSON
    include_fields: list[str] | None = None
    exclude_fields: list[str] | None = None
    batch_size: int = 1000
    compress: bool = False
    include_metadata: bool = True
