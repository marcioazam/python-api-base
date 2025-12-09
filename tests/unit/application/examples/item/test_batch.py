"""Unit tests for ItemExampleBatchService.

**Task: Phase 3 - Application Layer Tests**
**Requirements: 6.1, 6.2, 6.3, 6.4**
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from datetime import UTC, datetime
from decimal import Decimal

from application.common.batch.config import BatchConfig, BatchErrorStrategy
from application.examples.item.batch.batch import (
    BatchCreateRequest,
    BatchUpdateRequest,
    ItemExampleBatchService,
    _apply_batch_update_fields,
)
from domain.examples.item.entity import ItemExample, ItemExampleStatus, Money


def create_mock_item_entity(
    item_id: str = "item-123",
    name: str = "Test Item",
) -> MagicMock:
    """Create a fully configured mock ItemExample entity."""
    entity = MagicMock(spec=ItemExample)
    entity.id = item_id
    entity.name = name
    entity.description = "Test description"
    entity.sku = "SKU-001"
    entity.price = Money(Decimal("99.99"), "BRL")
    entity.quantity = 10
    entity.status = ItemExampleStatus.ACTIVE
    entity.category = "Electronics"
    entity.tags = ["tag1", "tag2"]
    entity.is_available = True
    entity.total_value = Money(Decimal("999.90"), "BRL")
    entity.created_at = datetime(2024, 1, 1, tzinfo=UTC)
    entity.updated_at = datetime(2024, 1, 2, tzinfo=UTC)
    entity.created_by = "user-1"
    entity.updated_by = "user-2"
    return entity


class TestBatchCreateRequest:
    """Tests for BatchCreateRequest dataclass."""

    def test_create_with_defaults(self) -> None:
        """Should create request with default values."""
        request = BatchCreateRequest(
            name="Test Item",
            sku="SKU-001",
            price_amount=10.0,
        )

        assert request.name == "Test Item"
        assert request.sku == "SKU-001"
        assert request.price_amount == 10.0
        assert request.price_currency == "BRL"
        assert request.description == ""
        assert request.quantity == 0
        assert request.category == ""
        assert request.tags == []

    def test_create_with_all_fields(self) -> None:
        """Should create request with all fields."""
        request = BatchCreateRequest(
            name="Test Item",
            sku="SKU-001",
            price_amount=10.0,
            price_currency="USD",
            description="A test item",
            quantity=5,
            category="Electronics",
            tags=["tag1", "tag2"],
        )

        assert request.price_currency == "USD"
        assert request.description == "A test item"
        assert request.quantity == 5
        assert request.category == "Electronics"
        assert request.tags == ["tag1", "tag2"]


class TestBatchUpdateRequest:
    """Tests for BatchUpdateRequest dataclass."""

    def test_create_with_id_only(self) -> None:
        """Should create request with only item_id."""
        request = BatchUpdateRequest(item_id="item-123")

        assert request.item_id == "item-123"
        assert request.name is None
        assert request.description is None
        assert request.price_amount is None
        assert request.quantity is None
        assert request.category is None

    def test_create_with_partial_fields(self) -> None:
        """Should create request with partial fields."""
        request = BatchUpdateRequest(
            item_id="item-123",
            name="Updated Name",
            quantity=10,
        )

        assert request.item_id == "item-123"
        assert request.name == "Updated Name"
        assert request.quantity == 10
        assert request.description is None


class TestApplyBatchUpdateFields:
    """Tests for _apply_batch_update_fields helper."""

    @pytest.fixture
    def mock_entity(self) -> MagicMock:
        """Create mock ItemExample entity."""
        entity = MagicMock(spec=ItemExample)
        entity.name = "Original Name"
        entity.description = "Original Description"
        entity.quantity = 10
        entity.category = "Original Category"
        entity.price = Money(100, "BRL")
        return entity

    def test_applies_name_update(self, mock_entity: MagicMock) -> None:
        """Should apply name update."""
        update = BatchUpdateRequest(item_id="123", name="New Name")

        _apply_batch_update_fields(mock_entity, update, "user-1")

        assert mock_entity.name == "New Name"
        mock_entity.mark_updated_by.assert_called_once_with("user-1")

    def test_applies_description_update(self, mock_entity: MagicMock) -> None:
        """Should apply description update."""
        update = BatchUpdateRequest(item_id="123", description="New Desc")

        _apply_batch_update_fields(mock_entity, update, "user-1")

        assert mock_entity.description == "New Desc"

    def test_applies_price_update(self, mock_entity: MagicMock) -> None:
        """Should apply price update preserving currency."""
        update = BatchUpdateRequest(item_id="123", price_amount=200.0)

        _apply_batch_update_fields(mock_entity, update, "user-1")

        assert mock_entity.price.amount == 200.0
        assert mock_entity.price.currency == "BRL"

    def test_applies_quantity_update(self, mock_entity: MagicMock) -> None:
        """Should apply quantity update."""
        update = BatchUpdateRequest(item_id="123", quantity=50)

        _apply_batch_update_fields(mock_entity, update, "user-1")

        assert mock_entity.quantity == 50

    def test_applies_category_update(self, mock_entity: MagicMock) -> None:
        """Should apply category update."""
        update = BatchUpdateRequest(item_id="123", category="New Category")

        _apply_batch_update_fields(mock_entity, update, "user-1")

        assert mock_entity.category == "New Category"

    def test_skips_none_fields(self, mock_entity: MagicMock) -> None:
        """Should skip None fields."""
        original_name = mock_entity.name
        update = BatchUpdateRequest(item_id="123")

        _apply_batch_update_fields(mock_entity, update, "user-1")

        # Name should not be changed
        assert mock_entity.name == original_name


class TestItemExampleBatchService:
    """Tests for ItemExampleBatchService."""

    @pytest.fixture
    def mock_repository(self) -> AsyncMock:
        """Create mock repository."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_repository: AsyncMock) -> ItemExampleBatchService:
        """Create batch service instance."""
        return ItemExampleBatchService(mock_repository)

    @pytest.fixture
    def service_fail_fast(self, mock_repository: AsyncMock) -> ItemExampleBatchService:
        """Create batch service with fail-fast strategy."""
        config = BatchConfig(
            chunk_size=100,
            error_strategy=BatchErrorStrategy.FAIL_FAST,
        )
        return ItemExampleBatchService(mock_repository, config)

    @pytest.mark.asyncio
    async def test_batch_create_success(
        self, service: ItemExampleBatchService, mock_repository: AsyncMock
    ) -> None:
        """Should create items successfully."""
        mock_entity = create_mock_item_entity()
        mock_repository.create.return_value = mock_entity

        items = [
            BatchCreateRequest(name="Item 1", sku="SKU-1", price_amount=10.0),
            BatchCreateRequest(name="Item 2", sku="SKU-2", price_amount=20.0),
        ]

        result = await service.batch_create(items, created_by="user-1")

        assert result.total_processed == 2
        assert len(result.succeeded) == 2
        assert len(result.failed) == 0
        assert mock_repository.create.call_count == 2

    @pytest.mark.asyncio
    async def test_batch_create_with_progress_callback(
        self, service: ItemExampleBatchService, mock_repository: AsyncMock
    ) -> None:
        """Should call progress callback."""
        mock_entity = create_mock_item_entity()
        mock_repository.create.return_value = mock_entity
        progress_calls: list[tuple[int, int]] = []

        def progress_callback(current: int, total: int) -> None:
            progress_calls.append((current, total))

        items = [
            BatchCreateRequest(name="Item 1", sku="SKU-1", price_amount=10.0),
            BatchCreateRequest(name="Item 2", sku="SKU-2", price_amount=20.0),
        ]

        await service.batch_create(items, progress_callback=progress_callback)

        assert progress_calls == [(1, 2), (2, 2)]

    @pytest.mark.asyncio
    async def test_batch_create_continues_on_error(
        self, service: ItemExampleBatchService, mock_repository: AsyncMock
    ) -> None:
        """Should continue on error with CONTINUE strategy."""
        mock_entity = create_mock_item_entity()
        mock_repository.create.side_effect = [
            Exception("First failed"),
            mock_entity,
        ]

        items = [
            BatchCreateRequest(name="Item 1", sku="SKU-1", price_amount=10.0),
            BatchCreateRequest(name="Item 2", sku="SKU-2", price_amount=20.0),
        ]

        result = await service.batch_create(items)

        assert result.total_processed == 2
        assert len(result.succeeded) == 1
        assert len(result.failed) == 1
        assert result.failed[0] == (0, "First failed")

    @pytest.mark.asyncio
    async def test_batch_create_fail_fast(
        self, service_fail_fast: ItemExampleBatchService, mock_repository: AsyncMock
    ) -> None:
        """Should raise on first error with FAIL_FAST strategy."""
        mock_repository.create.side_effect = Exception("Creation failed")

        items = [
            BatchCreateRequest(name="Item 1", sku="SKU-1", price_amount=10.0),
        ]

        with pytest.raises(Exception, match="Creation failed"):
            await service_fail_fast.batch_create(items)

    @pytest.mark.asyncio
    async def test_batch_update_success(
        self, service: ItemExampleBatchService, mock_repository: AsyncMock
    ) -> None:
        """Should update items successfully."""
        mock_entity = create_mock_item_entity()
        mock_repository.get.return_value = mock_entity
        mock_repository.update.return_value = mock_entity

        updates = [
            BatchUpdateRequest(item_id="item-1", name="Updated 1"),
            BatchUpdateRequest(item_id="item-2", name="Updated 2"),
        ]

        result = await service.batch_update(updates, updated_by="user-1")

        assert result.total_processed == 2
        assert len(result.succeeded) == 2
        assert len(result.failed) == 0

    @pytest.mark.asyncio
    async def test_batch_update_not_found(
        self, service: ItemExampleBatchService, mock_repository: AsyncMock
    ) -> None:
        """Should handle not found items."""
        mock_repository.get.return_value = None

        updates = [BatchUpdateRequest(item_id="nonexistent", name="Updated")]

        result = await service.batch_update(updates)

        assert result.total_processed == 1
        assert len(result.succeeded) == 0
        assert len(result.failed) == 1
        assert "not found" in result.failed[0][1]

    @pytest.mark.asyncio
    async def test_batch_delete_soft_delete(
        self, service: ItemExampleBatchService, mock_repository: AsyncMock
    ) -> None:
        """Should soft delete items."""
        mock_entity = MagicMock(spec=ItemExample)
        mock_repository.get.return_value = mock_entity
        mock_repository.update.return_value = mock_entity

        result = await service.batch_delete(
            ["item-1", "item-2"],
            deleted_by="user-1",
            hard_delete=False,
        )

        assert result.total_processed == 2
        assert len(result.succeeded) == 2
        mock_entity.soft_delete.assert_called()
        mock_repository.update.assert_called()

    @pytest.mark.asyncio
    async def test_batch_delete_hard_delete(
        self, service: ItemExampleBatchService, mock_repository: AsyncMock
    ) -> None:
        """Should hard delete items."""
        mock_entity = MagicMock(spec=ItemExample)
        mock_repository.get.return_value = mock_entity

        result = await service.batch_delete(
            ["item-1"],
            deleted_by="user-1",
            hard_delete=True,
        )

        assert result.total_processed == 1
        assert len(result.succeeded) == 1
        mock_repository.delete.assert_called_once_with("item-1")

    @pytest.mark.asyncio
    async def test_batch_delete_not_found(
        self, service: ItemExampleBatchService, mock_repository: AsyncMock
    ) -> None:
        """Should handle not found items in delete."""
        mock_repository.get.return_value = None

        result = await service.batch_delete(["nonexistent"])

        assert result.total_processed == 1
        assert len(result.failed) == 1
        assert "not found" in result.failed[0][1]
