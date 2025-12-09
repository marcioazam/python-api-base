"""Unit tests for ItemExample export/import services.

**Task: Phase 3 - Application Layer Tests**
**Requirements: 7.1, 7.2, 7.3, 7.4, 7.5**
"""

import json
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from application.examples.item.export.export import (
    ExportFormat,
    ExportMetadata,
    ExportResult,
    ImportResult,
    ItemExampleExportService,
    ItemExampleImportService,
)
from domain.examples.item.entity import ItemExample, ItemExampleStatus, Money


class TestExportFormat:
    """Tests for ExportFormat enum."""

    def test_json_format(self) -> None:
        """Should have JSON format."""
        assert ExportFormat.JSON.value == "json"

    def test_csv_format(self) -> None:
        """Should have CSV format."""
        assert ExportFormat.CSV.value == "csv"

    def test_jsonl_format(self) -> None:
        """Should have JSONL format."""
        assert ExportFormat.JSONL.value == "jsonl"


class TestExportMetadata:
    """Tests for ExportMetadata dataclass."""

    def test_create_metadata(self) -> None:
        """Should create metadata with all fields."""
        now = datetime.now(UTC)
        metadata = ExportMetadata(
            format="json",
            record_count=10,
            export_timestamp=now,
            checksum="abc123",
        )

        assert metadata.format == "json"
        assert metadata.record_count == 10
        assert metadata.export_timestamp == now
        assert metadata.checksum == "abc123"
        assert metadata.version == "1.0"


class TestExportResult:
    """Tests for ExportResult dataclass."""

    def test_create_result(self) -> None:
        """Should create export result."""
        metadata = ExportMetadata(
            format="json",
            record_count=5,
            export_timestamp=datetime.now(UTC),
            checksum="abc",
        )
        result = ExportResult(
            data='{"items": []}',
            metadata=metadata,
            content_type="application/json",
        )

        assert result.data == '{"items": []}'
        assert result.content_type == "application/json"


class TestImportResult:
    """Tests for ImportResult dataclass."""

    def test_create_with_defaults(self) -> None:
        """Should create with default values."""
        result = ImportResult()

        assert result.processed == 0
        assert result.imported == 0
        assert result.skipped == 0
        assert result.failed == 0
        assert result.errors == []

    def test_create_with_values(self) -> None:
        """Should create with specified values."""
        result = ImportResult(
            processed=10,
            imported=8,
            skipped=1,
            failed=1,
            errors=["Error 1"],
        )

        assert result.processed == 10
        assert result.imported == 8
        assert result.failed == 1


class TestItemExampleExportService:
    """Tests for ItemExampleExportService."""

    @pytest.fixture
    def mock_repository(self) -> AsyncMock:
        """Create mock repository."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_repository: AsyncMock) -> ItemExampleExportService:
        """Create export service."""
        return ItemExampleExportService(mock_repository)

    @pytest.fixture
    def mock_item(self) -> MagicMock:
        """Create mock ItemExample."""
        item = MagicMock(spec=ItemExample)
        item.id = "item-123"
        item.name = "Test Item"
        item.description = "A test item"
        item.sku = "SKU-001"
        item.price = Money(Decimal("99.99"), "BRL")
        item.quantity = 10
        item.status = ItemExampleStatus.ACTIVE
        item.category = "Electronics"
        item.tags = ["tag1", "tag2"]
        item.is_available = True
        item.total_value = Money(Decimal("999.90"), "BRL")
        item.created_at = datetime(2024, 1, 1, tzinfo=UTC)
        item.updated_at = datetime(2024, 1, 2, tzinfo=UTC)
        item.created_by = "user-1"
        item.updated_by = "user-2"
        return item

    @pytest.mark.asyncio
    async def test_export_to_json(
        self, service: ItemExampleExportService, mock_repository: AsyncMock, mock_item: MagicMock
    ) -> None:
        """Should export items to JSON format."""
        mock_repository.get_all.return_value = [mock_item]

        result = await service.export_to_json()

        assert result.content_type == "application/json"
        assert result.metadata.format == "json"
        assert result.metadata.record_count == 1
        assert len(result.metadata.checksum) == 16

        data = json.loads(result.data)
        assert data["version"] == "1.0"
        assert len(data["data"]) == 1
        assert data["data"][0]["name"] == "Test Item"

    @pytest.mark.asyncio
    async def test_export_to_json_with_items(
        self, service: ItemExampleExportService, mock_item: MagicMock
    ) -> None:
        """Should export provided items to JSON."""
        result = await service.export_to_json(items=[mock_item])

        assert result.metadata.record_count == 1

    @pytest.mark.asyncio
    async def test_export_to_csv(
        self, service: ItemExampleExportService, mock_repository: AsyncMock, mock_item: MagicMock
    ) -> None:
        """Should export items to CSV format."""
        mock_repository.get_all.return_value = [mock_item]

        result = await service.export_to_csv()

        assert result.content_type == "text/csv"
        assert result.metadata.format == "csv"
        assert "id,name,description" in result.data
        assert "Test Item" in result.data

    @pytest.mark.asyncio
    async def test_export_to_csv_empty(
        self, service: ItemExampleExportService, mock_repository: AsyncMock
    ) -> None:
        """Should handle empty export to CSV."""
        mock_repository.get_all.return_value = []

        result = await service.export_to_csv()

        assert result.metadata.record_count == 0

    @pytest.mark.asyncio
    async def test_export_to_jsonl(
        self, service: ItemExampleExportService, mock_repository: AsyncMock, mock_item: MagicMock
    ) -> None:
        """Should export items to JSONL format."""
        mock_repository.get_all.return_value = [mock_item]

        result = await service.export_to_jsonl()

        assert result.content_type == "application/x-ndjson"
        assert result.metadata.format == "jsonl"

        lines = result.data.strip().split("\n")
        assert len(lines) == 1
        item_data = json.loads(lines[0])
        assert item_data["name"] == "Test Item"

    @pytest.mark.asyncio
    async def test_export_generic_json(
        self, service: ItemExampleExportService, mock_repository: AsyncMock, mock_item: MagicMock
    ) -> None:
        """Should export using generic export method with JSON."""
        mock_repository.get_all.return_value = [mock_item]

        result = await service.export(ExportFormat.JSON)

        assert result.metadata.format == "json"

    @pytest.mark.asyncio
    async def test_export_generic_csv(
        self, service: ItemExampleExportService, mock_repository: AsyncMock, mock_item: MagicMock
    ) -> None:
        """Should export using generic export method with CSV."""
        mock_repository.get_all.return_value = [mock_item]

        result = await service.export(ExportFormat.CSV)

        assert result.metadata.format == "csv"

    @pytest.mark.asyncio
    async def test_export_generic_jsonl(
        self, service: ItemExampleExportService, mock_repository: AsyncMock, mock_item: MagicMock
    ) -> None:
        """Should export using generic export method with JSONL."""
        mock_repository.get_all.return_value = [mock_item]

        result = await service.export(ExportFormat.JSONL)

        assert result.metadata.format == "jsonl"


class TestItemExampleImportService:
    """Tests for ItemExampleImportService."""

    @pytest.fixture
    def mock_repository(self) -> AsyncMock:
        """Create mock repository."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_repository: AsyncMock) -> ItemExampleImportService:
        """Create import service."""
        return ItemExampleImportService(mock_repository)

    @pytest.mark.asyncio
    async def test_import_from_json(
        self, service: ItemExampleImportService, mock_repository: AsyncMock
    ) -> None:
        """Should import items from JSON."""
        json_data = json.dumps({
            "data": [
                {
                    "name": "Item 1",
                    "description": "Desc 1",
                    "sku": "SKU-1",
                    "price": {"amount": "10.00", "currency": "BRL"},
                    "quantity": 5,
                    "category": "Cat1",
                    "tags": ["tag1"],
                }
            ]
        })

        result = await service.import_from_json(json_data, created_by="user-1")

        assert result.processed == 1
        assert result.imported == 1
        assert result.failed == 0
        mock_repository.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_import_from_json_invalid(
        self, service: ItemExampleImportService
    ) -> None:
        """Should handle invalid JSON."""
        result = await service.import_from_json("not valid json")

        assert result.processed == 0
        assert result.imported == 0
        assert len(result.errors) == 1
        assert "Invalid JSON" in result.errors[0]

    @pytest.mark.asyncio
    async def test_import_from_json_with_errors(
        self, service: ItemExampleImportService, mock_repository: AsyncMock
    ) -> None:
        """Should handle import errors."""
        mock_repository.create.side_effect = Exception("DB error")
        json_data = json.dumps({
            "data": [{"name": "Item 1", "sku": "SKU-1"}]
        })

        result = await service.import_from_json(json_data)

        assert result.processed == 1
        assert result.imported == 0
        assert result.failed == 1

    @pytest.mark.asyncio
    async def test_import_from_csv(
        self, service: ItemExampleImportService, mock_repository: AsyncMock
    ) -> None:
        """Should import items from CSV."""
        csv_data = """name,description,sku,price_amount,price_currency,quantity,category,tags
Item 1,Desc 1,SKU-1,10.00,BRL,5,Cat1,tag1
Item 2,Desc 2,SKU-2,20.00,USD,10,Cat2,tag2"""

        result = await service.import_from_csv(csv_data, created_by="user-1")

        assert result.processed == 2
        assert result.imported == 2
        assert mock_repository.create.call_count == 2

    @pytest.mark.asyncio
    async def test_import_from_csv_with_errors(
        self, service: ItemExampleImportService, mock_repository: AsyncMock
    ) -> None:
        """Should handle CSV import errors."""
        mock_repository.create.side_effect = Exception("DB error")
        csv_data = """name,description,sku,price_amount,price_currency,quantity,category,tags
Item 1,Desc 1,SKU-1,10.00,BRL,5,Cat1,tag1"""

        result = await service.import_from_csv(csv_data)

        assert result.processed == 1
        assert result.failed == 1

    @pytest.mark.asyncio
    async def test_import_from_jsonl(
        self, service: ItemExampleImportService, mock_repository: AsyncMock
    ) -> None:
        """Should import items from JSONL."""
        jsonl_data = """{"name": "Item 1", "sku": "SKU-1", "price": {"amount": "10", "currency": "BRL"}}
{"name": "Item 2", "sku": "SKU-2", "price": {"amount": "20", "currency": "USD"}}"""

        result = await service.import_from_jsonl(jsonl_data, created_by="user-1")

        assert result.processed == 2
        assert result.imported == 2

    @pytest.mark.asyncio
    async def test_import_from_jsonl_skips_empty_lines(
        self, service: ItemExampleImportService, mock_repository: AsyncMock
    ) -> None:
        """Should skip empty lines in JSONL."""
        jsonl_data = """{"name": "Item 1", "sku": "SKU-1", "price": {"amount": "10", "currency": "BRL"}}

{"name": "Item 2", "sku": "SKU-2", "price": {"amount": "20", "currency": "USD"}}"""

        result = await service.import_from_jsonl(jsonl_data)

        assert result.processed == 2
        assert result.imported == 2

    @pytest.mark.asyncio
    async def test_import_from_jsonl_with_errors(
        self, service: ItemExampleImportService, mock_repository: AsyncMock
    ) -> None:
        """Should handle JSONL import errors."""
        mock_repository.create.side_effect = Exception("DB error")
        jsonl_data = """{"name": "Item 1", "sku": "SKU-1"}"""

        result = await service.import_from_jsonl(jsonl_data)

        assert result.processed == 1
        assert result.failed == 1
