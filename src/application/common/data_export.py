"""Generic Data Export/Import Service."""

from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from typing import Protocol, Any
import json
import csv
import io


class ExportFormat(Enum):
    """Supported export formats."""
    JSON = "json"
    CSV = "csv"
    JSONL = "jsonl"
    PARQUET = "parquet"


@dataclass
class ExportConfig:
    """Export configuration."""
    format: ExportFormat = ExportFormat.JSON
    include_fields: list[str] | None = None
    exclude_fields: list[str] | None = None
    batch_size: int = 1000
    compress: bool = False
    include_metadata: bool = True


@dataclass
class ExportResult:
    """Export operation result."""
    format: ExportFormat
    record_count: int
    file_size_bytes: int
    duration_ms: float
    checksum: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ImportResult:
    """Import operation result."""
    records_processed: int
    records_imported: int
    records_skipped: int
    records_failed: int
    errors: list[str] = field(default_factory=list)
    duration_ms: float = 0.0


class DataSerializer[T](Protocol):
    """Protocol for data serialization."""

    def to_dict(self, obj: T) -> dict[str, Any]: ...
    def from_dict(self, data: dict[str, Any]) -> T: ...


class DataExporter[T]:
    """Generic data exporter."""

    def __init__(self, serializer: DataSerializer[T]) -> None:
        self._serializer = serializer

    def _filter_fields(
        self,
        data: dict[str, Any],
        config: ExportConfig
    ) -> dict[str, Any]:
        if config.include_fields:
            return {k: v for k, v in data.items() if k in config.include_fields}
        if config.exclude_fields:
            return {k: v for k, v in data.items() if k not in config.exclude_fields}
        return data

    def _compute_checksum(self, content: bytes) -> str:
        import hashlib
        return hashlib.sha256(content).hexdigest()[:16]

    def export_json(
        self,
        records: list[T],
        config: ExportConfig
    ) -> tuple[bytes, ExportResult]:
        """Export records to JSON."""
        import time
        start = time.perf_counter()

        data = [
            self._filter_fields(self._serializer.to_dict(r), config)
            for r in records
        ]

        if config.include_metadata:
            output = {
                "metadata": {
                    "exported_at": datetime.now(UTC).isoformat(),
                    "record_count": len(data),
                    "format": "json"
                },
                "data": data
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
            checksum=self._compute_checksum(content)
        )


    def export_csv(
        self,
        records: list[T],
        config: ExportConfig
    ) -> tuple[bytes, ExportResult]:
        """Export records to CSV."""
        import time
        start = time.perf_counter()

        if not records:
            return b"", ExportResult(
                format=ExportFormat.CSV,
                record_count=0,
                file_size_bytes=0,
                duration_ms=0,
                checksum=""
            )

        data = [
            self._filter_fields(self._serializer.to_dict(r), config)
            for r in records
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
            checksum=self._compute_checksum(content)
        )

    def export_jsonl(
        self,
        records: list[T],
        config: ExportConfig
    ) -> tuple[bytes, ExportResult]:
        """Export records to JSON Lines."""
        import time
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
            checksum=self._compute_checksum(content)
        )

    def export(
        self,
        records: list[T],
        config: ExportConfig
    ) -> tuple[bytes, ExportResult]:
        """Export records in specified format."""
        if config.format == ExportFormat.JSON:
            return self.export_json(records, config)
        elif config.format == ExportFormat.CSV:
            return self.export_csv(records, config)
        elif config.format == ExportFormat.JSONL:
            return self.export_jsonl(records, config)
        else:
            raise ValueError(f"Unsupported format: {config.format}")


class DataImporter[T]:
    """Generic data importer."""

    def __init__(self, serializer: DataSerializer[T]) -> None:
        self._serializer = serializer

    def import_json(self, content: bytes) -> tuple[list[T], ImportResult]:
        """Import records from JSON."""
        import time
        start = time.perf_counter()

        result = ImportResult(
            records_processed=0,
            records_imported=0,
            records_skipped=0,
            records_failed=0
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
        import time
        start = time.perf_counter()

        result = ImportResult(
            records_processed=0,
            records_imported=0,
            records_skipped=0,
            records_failed=0
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
        import time
        start = time.perf_counter()

        result = ImportResult(
            records_processed=0,
            records_imported=0,
            records_skipped=0,
            records_failed=0
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
        self,
        content: bytes,
        format: ExportFormat
    ) -> tuple[list[T], ImportResult]:
        """Import records from specified format."""
        if format == ExportFormat.JSON:
            return self.import_json(content)
        elif format == ExportFormat.CSV:
            return self.import_csv(content)
        elif format == ExportFormat.JSONL:
            return self.import_jsonl(content)
        else:
            raise ValueError(f"Unsupported format: {format}")
