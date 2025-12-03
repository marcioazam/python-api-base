"""Data export/import service for ItemExample.

**Feature: application-common-integration**
**Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5**
"""

import csv
import hashlib
import io
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from application.examples.item.dtos import ItemExampleResponse
from application.examples.item.mapper import ItemExampleMapper
from domain.examples.item.entity import ItemExample


class ExportFormat(str, Enum):
    """Supported export formats."""
    
    JSON = "json"
    CSV = "csv"
    JSONL = "jsonl"


@dataclass
class ExportMetadata:
    """Metadata for export operations."""
    
    format: str
    record_count: int
    export_timestamp: datetime
    checksum: str
    version: str = "1.0"


@dataclass
class ExportResult:
    """Result of an export operation."""
    
    data: str | bytes
    metadata: ExportMetadata
    content_type: str


@dataclass
class ImportResult:
    """Result of an import operation."""
    
    processed: int = 0
    imported: int = 0
    skipped: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)


class ItemExampleExportService:
    """Service for exporting ItemExample data in multiple formats."""
    
    def __init__(self, repository: Any) -> None:
        """Initialize export service.
        
        Args:
            repository: ItemExample repository.
        """
        self._repo = repository
        self._mapper = ItemExampleMapper()
    
    async def export_to_json(
        self,
        items: list[ItemExample] | None = None,
        **filters: Any,
    ) -> ExportResult:
        """Export items to JSON format.
        
        Args:
            items: Optional list of items to export.
            **filters: Filters for querying items if not provided.
        
        Returns:
            ExportResult with JSON data and metadata.
        """
        if items is None:
            items = await self._repo.get_all(**filters)
        
        dtos = [self._mapper.to_dto(item) for item in items]
        data_list = [self._dto_to_dict(dto) for dto in dtos]
        
        export_data = {
            "version": "1.0",
            "export_timestamp": datetime.utcnow().isoformat(),
            "record_count": len(data_list),
            "data": data_list,
        }
        
        json_str = json.dumps(export_data, indent=2, default=str)
        checksum = self._compute_checksum(json_str)
        
        return ExportResult(
            data=json_str,
            metadata=ExportMetadata(
                format=ExportFormat.JSON.value,
                record_count=len(data_list),
                export_timestamp=datetime.utcnow(),
                checksum=checksum,
            ),
            content_type="application/json",
        )
    
    async def export_to_csv(
        self,
        items: list[ItemExample] | None = None,
        **filters: Any,
    ) -> ExportResult:
        """Export items to CSV format.
        
        Args:
            items: Optional list of items to export.
            **filters: Filters for querying items if not provided.
        
        Returns:
            ExportResult with CSV data and metadata.
        """
        if items is None:
            items = await self._repo.get_all(**filters)
        
        dtos = [self._mapper.to_dto(item) for item in items]
        
        output = io.StringIO()
        if dtos:
            fieldnames = [
                "id", "name", "description", "sku", "price_amount",
                "price_currency", "quantity", "status", "category",
                "tags", "is_available", "created_at", "updated_at",
            ]
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            
            for dto in dtos:
                writer.writerow({
                    "id": dto.id,
                    "name": dto.name,
                    "description": dto.description,
                    "sku": dto.sku,
                    "price_amount": str(dto.price.amount),
                    "price_currency": dto.price.currency,
                    "quantity": dto.quantity,
                    "status": dto.status,
                    "category": dto.category,
                    "tags": ",".join(dto.tags),
                    "is_available": dto.is_available,
                    "created_at": dto.created_at.isoformat() if dto.created_at else "",
                    "updated_at": dto.updated_at.isoformat() if dto.updated_at else "",
                })
        
        csv_str = output.getvalue()
        checksum = self._compute_checksum(csv_str)
        
        return ExportResult(
            data=csv_str,
            metadata=ExportMetadata(
                format=ExportFormat.CSV.value,
                record_count=len(dtos),
                export_timestamp=datetime.utcnow(),
                checksum=checksum,
            ),
            content_type="text/csv",
        )
    
    async def export_to_jsonl(
        self,
        items: list[ItemExample] | None = None,
        **filters: Any,
    ) -> ExportResult:
        """Export items to JSONL (JSON Lines) format.
        
        Args:
            items: Optional list of items to export.
            **filters: Filters for querying items if not provided.
        
        Returns:
            ExportResult with JSONL data and metadata.
        """
        if items is None:
            items = await self._repo.get_all(**filters)
        
        dtos = [self._mapper.to_dto(item) for item in items]
        lines = [json.dumps(self._dto_to_dict(dto), default=str) for dto in dtos]
        jsonl_str = "\n".join(lines)
        
        checksum = self._compute_checksum(jsonl_str)
        
        return ExportResult(
            data=jsonl_str,
            metadata=ExportMetadata(
                format=ExportFormat.JSONL.value,
                record_count=len(dtos),
                export_timestamp=datetime.utcnow(),
                checksum=checksum,
            ),
            content_type="application/x-ndjson",
        )
    
    async def export(
        self,
        format: ExportFormat,
        items: list[ItemExample] | None = None,
        **filters: Any,
    ) -> ExportResult:
        """Export items in the specified format.
        
        Args:
            format: Export format (JSON, CSV, JSONL).
            items: Optional list of items to export.
            **filters: Filters for querying items if not provided.
        
        Returns:
            ExportResult with data and metadata.
        """
        if format == ExportFormat.JSON:
            return await self.export_to_json(items, **filters)
        elif format == ExportFormat.CSV:
            return await self.export_to_csv(items, **filters)
        elif format == ExportFormat.JSONL:
            return await self.export_to_jsonl(items, **filters)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def _dto_to_dict(self, dto: ItemExampleResponse) -> dict[str, Any]:
        """Convert DTO to dictionary for serialization."""
        return {
            "id": dto.id,
            "name": dto.name,
            "description": dto.description,
            "sku": dto.sku,
            "price": {"amount": str(dto.price.amount), "currency": dto.price.currency},
            "quantity": dto.quantity,
            "status": dto.status,
            "category": dto.category,
            "tags": dto.tags,
            "is_available": dto.is_available,
            "created_at": dto.created_at.isoformat() if dto.created_at else None,
            "updated_at": dto.updated_at.isoformat() if dto.updated_at else None,
            "created_by": dto.created_by,
            "updated_by": dto.updated_by,
        }
    
    def _compute_checksum(self, data: str) -> str:
        """Compute SHA-256 checksum (first 16 hex chars)."""
        full_hash = hashlib.sha256(data.encode()).hexdigest()
        return full_hash[:16]


class ItemExampleImportService:
    """Service for importing ItemExample data from multiple formats."""
    
    def __init__(self, repository: Any) -> None:
        """Initialize import service.
        
        Args:
            repository: ItemExample repository.
        """
        self._repo = repository
        self._mapper = ItemExampleMapper()
    
    async def import_from_json(
        self,
        data: str,
        created_by: str = "system",
    ) -> ImportResult:
        """Import items from JSON format.
        
        Args:
            data: JSON string with items data.
            created_by: User performing the import.
        
        Returns:
            ImportResult with counts.
        """
        result = ImportResult()
        
        try:
            parsed = json.loads(data)
            items_data = parsed.get("data", []) if isinstance(parsed, dict) else parsed
        except json.JSONDecodeError as e:
            result.errors.append(f"Invalid JSON: {e}")
            return result
        
        for item_data in items_data:
            result.processed += 1
            try:
                entity = self._dict_to_entity(item_data, created_by)
                await self._repo.create(entity)
                result.imported += 1
            except Exception as e:
                result.failed += 1
                result.errors.append(f"Row {result.processed}: {e}")
        
        return result
    
    async def import_from_csv(
        self,
        data: str,
        created_by: str = "system",
    ) -> ImportResult:
        """Import items from CSV format.
        
        Args:
            data: CSV string with items data.
            created_by: User performing the import.
        
        Returns:
            ImportResult with counts.
        """
        result = ImportResult()
        
        reader = csv.DictReader(io.StringIO(data))
        for row in reader:
            result.processed += 1
            try:
                entity = self._csv_row_to_entity(row, created_by)
                await self._repo.create(entity)
                result.imported += 1
            except Exception as e:
                result.failed += 1
                result.errors.append(f"Row {result.processed}: {e}")
        
        return result
    
    async def import_from_jsonl(
        self,
        data: str,
        created_by: str = "system",
    ) -> ImportResult:
        """Import items from JSONL format.
        
        Args:
            data: JSONL string with items data.
            created_by: User performing the import.
        
        Returns:
            ImportResult with counts.
        """
        result = ImportResult()
        
        for line in data.strip().split("\n"):
            if not line.strip():
                continue
            
            result.processed += 1
            try:
                item_data = json.loads(line)
                entity = self._dict_to_entity(item_data, created_by)
                await self._repo.create(entity)
                result.imported += 1
            except Exception as e:
                result.failed += 1
                result.errors.append(f"Line {result.processed}: {e}")
        
        return result
    
    def _dict_to_entity(self, data: dict[str, Any], created_by: str) -> ItemExample:
        """Convert dictionary to ItemExample entity."""
        from decimal import Decimal
        from domain.examples.item.entity import Money
        
        price_data = data.get("price", {})
        price_amount = Decimal(str(price_data.get("amount", 0)))
        price_currency = price_data.get("currency", "BRL")
        
        return ItemExample.create(
            name=data.get("name", ""),
            description=data.get("description", ""),
            sku=data.get("sku", ""),
            price=Money(price_amount, price_currency),
            quantity=int(data.get("quantity", 0)),
            category=data.get("category", ""),
            tags=data.get("tags", []),
            created_by=created_by,
        )
    
    def _csv_row_to_entity(self, row: dict[str, str], created_by: str) -> ItemExample:
        """Convert CSV row to ItemExample entity."""
        from decimal import Decimal
        from domain.examples.item.entity import Money
        
        tags = row.get("tags", "").split(",") if row.get("tags") else []
        
        return ItemExample.create(
            name=row.get("name", ""),
            description=row.get("description", ""),
            sku=row.get("sku", ""),
            price=Money(
                Decimal(row.get("price_amount", "0")),
                row.get("price_currency", "BRL"),
            ),
            quantity=int(row.get("quantity", 0)),
            category=row.get("category", ""),
            tags=[t.strip() for t in tags if t.strip()],
            created_by=created_by,
        )
