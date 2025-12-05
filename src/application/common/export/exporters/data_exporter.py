"""Generic data exporter.

**Feature: application-layer-code-review-2025**
**Refactored: Split from data_export.py for one-class-per-file compliance**
"""

import csv
import hashlib
import io
import json
import time
from datetime import UTC, datetime
from typing import Any

from application.common.export.config.export_config import ExportConfig
from application.common.export.formats.export_format import ExportFormat
from application.common.export.results.export_result import ExportResult
from application.common.export.serializers.data_serializer import DataSerializer


class DataExporter[T]:
    """Generic data exporter."""

    def __init__(self, serializer: DataSerializer[T]) -> None:
        self._serializer = serializer

    def _filter_fields(
        self, data: dict[str, Any], config: ExportConfig
    ) -> dict[str, Any]:
        if config.include_fields:
            return {k: v for k, v in data.items() if k in config.include_fields}
        if config.exclude_fields:
            return {k: v for k, v in data.items() if k not in config.exclude_fields}
        return data

    def _compute_checksum(self, content: bytes) -> str:
        """Compute SHA-256 checksum (truncated to 16 chars)."""
        return hashlib.sha256(content).hexdigest()[:16]

    def export_json(
        self, records: list[T], config: ExportConfig
    ) -> tuple[bytes, ExportResult]:
        """Export records to JSON."""
        start = time.perf_counter()

        data = [
            self._filter_fields(self._serializer.to_dict(r), config) for r in records
        ]

        if config.include_metadata:
            output = {
                "metadata": {
                    "exported_at": datetime.now(UTC).isoformat(),
                    "record_count": len(data),
                    "format": "json",
                },
                "data": data,
            }
        else:
            output = data

        content = json.dumps(output, indent=2, default=str).encode()
        duration = (time.perf_counter() - start) * 1000

        return content, ExportResult(
            format=ExportFormat.JSON,
            record_count=len(records),
            file_size_bytes=len(content),
            duration_ms=duration,
            checksum=self._compute_checksum(content),
        )

    def export_csv(
        self, records: list[T], config: ExportConfig
    ) -> tuple[bytes, ExportResult]:
        """Export records to CSV."""
        start = time.perf_counter()

        if not records:
            return b"", ExportResult(
                format=ExportFormat.CSV,
                record_count=0,
                file_size_bytes=0,
                duration_ms=0,
                checksum="",
            )

        data = [
            self._filter_fields(self._serializer.to_dict(r), config) for r in records
        ]

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        for row in data:
            writer.writerow({k: str(v) for k, v in row.items()})

        content = output.getvalue().encode()
        duration = (time.perf_counter() - start) * 1000

        return content, ExportResult(
            format=ExportFormat.CSV,
            record_count=len(records),
            file_size_bytes=len(content),
            duration_ms=duration,
            checksum=self._compute_checksum(content),
        )

    def export_jsonl(
        self, records: list[T], config: ExportConfig
    ) -> tuple[bytes, ExportResult]:
        """Export records to JSON Lines."""
        start = time.perf_counter()

        lines = []
        for record in records:
            data = self._filter_fields(self._serializer.to_dict(record), config)
            lines.append(json.dumps(data, default=str))

        content = "\n".join(lines).encode()
        duration = (time.perf_counter() - start) * 1000

        return content, ExportResult(
            format=ExportFormat.JSONL,
            record_count=len(records),
            file_size_bytes=len(content),
            duration_ms=duration,
            checksum=self._compute_checksum(content),
        )

    def export(
        self, records: list[T], config: ExportConfig
    ) -> tuple[bytes, ExportResult]:
        """Export records in specified format."""
        if config.format == ExportFormat.JSON:
            return self.export_json(records, config)
        if config.format == ExportFormat.CSV:
            return self.export_csv(records, config)
        if config.format == ExportFormat.JSONL:
            return self.export_jsonl(records, config)
        raise ValueError(f"Unsupported format: {config.format}")
