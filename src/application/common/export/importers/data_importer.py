"""Generic data importer.

**Feature: application-layer-code-review-2025**
**Refactored: Split from data_export.py for one-class-per-file compliance**
"""

import csv
import io
import json
import time

from application.common.export.formats.export_format import ExportFormat
from application.common.export.results.import_result import ImportResult
from application.common.export.serializers.data_serializer import DataSerializer


class DataImporter[T]:
    """Generic data importer."""

    def __init__(self, serializer: DataSerializer[T]) -> None:
        self._serializer = serializer

    def import_json(self, content: bytes) -> tuple[list[T], ImportResult]:
        """Import records from JSON."""
        start = time.perf_counter()

        result = ImportResult(
            records_processed=0, records_imported=0, records_skipped=0, records_failed=0
        )

        records: list[T] = []
        try:
            data = json.loads(content.decode())
            if isinstance(data, dict) and "data" in data:
                data = data["data"]

            for item in data:
                result.records_processed += 1
                try:
                    record = self._serializer.from_dict(item)
                    records.append(record)
                    result.records_imported += 1
                except Exception as e:
                    result.records_failed += 1
                    result.errors.append(str(e))

        except Exception as e:
            result.errors.append(f"Parse error: {e}")

        result.duration_ms = (time.perf_counter() - start) * 1000
        return records, result

    def import_csv(self, content: bytes) -> tuple[list[T], ImportResult]:
        """Import records from CSV."""
        start = time.perf_counter()

        result = ImportResult(
            records_processed=0, records_imported=0, records_skipped=0, records_failed=0
        )

        records: list[T] = []
        try:
            reader = csv.DictReader(io.StringIO(content.decode()))
            for row in reader:
                result.records_processed += 1
                try:
                    record = self._serializer.from_dict(dict(row))
                    records.append(record)
                    result.records_imported += 1
                except Exception as e:
                    result.records_failed += 1
                    result.errors.append(str(e))

        except Exception as e:
            result.errors.append(f"Parse error: {e}")

        result.duration_ms = (time.perf_counter() - start) * 1000
        return records, result

    def import_jsonl(self, content: bytes) -> tuple[list[T], ImportResult]:
        """Import records from JSON Lines."""
        start = time.perf_counter()

        result = ImportResult(
            records_processed=0, records_imported=0, records_skipped=0, records_failed=0
        )

        records: list[T] = []
        for line in content.decode().strip().split("\n"):
            if not line:
                continue
            result.records_processed += 1
            try:
                data = json.loads(line)
                record = self._serializer.from_dict(data)
                records.append(record)
                result.records_imported += 1
            except Exception as e:
                result.records_failed += 1
                result.errors.append(str(e))

        result.duration_ms = (time.perf_counter() - start) * 1000
        return records, result

    def import_data(
        self, content: bytes, format: ExportFormat
    ) -> tuple[list[T], ImportResult]:
        """Import records from specified format."""
        if format == ExportFormat.JSON:
            return self.import_json(content)
        if format == ExportFormat.CSV:
            return self.import_csv(content)
        if format == ExportFormat.JSONL:
            return self.import_jsonl(content)
        raise ValueError(f"Unsupported format: {format}")
