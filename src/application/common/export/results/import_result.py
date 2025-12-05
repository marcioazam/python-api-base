"""Import result dataclass.

**Feature: application-layer-code-review-2025**
**Refactored: Split from data_export.py for one-class-per-file compliance**
"""

from dataclasses import dataclass, field


@dataclass
class ImportResult:
    """Import operation result."""

    records_processed: int
    records_imported: int
    records_skipped: int
    records_failed: int
    errors: list[str] = field(default_factory=list)
    duration_ms: float = 0.0
