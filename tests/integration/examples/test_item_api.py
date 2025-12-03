"""Integration tests for ItemExample API.

**Feature: application-common-integration**
**Validates: Requirements 9.3**
"""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient


class MockItemRepository:
    """Mock repository for testing."""
    
    def __init__(self) -> None:
        self._items: dict[str, MagicMock] = {}
        self._counter = 0
    
    async def get(self, item_id: str) -> MagicMock | None:
        return self._items.get(item_id)
    
    async def get_by_sku(self, sku: str) -> MagicMock | None:
        for item in self._items.values():
            if item.sku == sku:
                return item
        return None
    
    async def create(self, entity: MagicMock) -> MagicMock:
        self._items[entity.id] = entity
        return entity
    
    async def update(self, entity: MagicMock) -> MagicMock:
        self._items[entity.id] = entity
        return entity
    
    async def get_all(self, **kwargs) -> list[MagicMock]:
        return list(self._items.values())
    
    async def count(self, **kwargs) -> int:
        return len(self._items)


class TestItemExampleCRUD:
    """Integration tests for ItemExample CRUD operations."""

    def test_create_item_command_structure(self) -> None:
        """Test CreateItemCommand has correct structure."""
        from application.examples.item.commands import CreateItemCommand
        
        command = CreateItemCommand(
            name="Test Item",
            sku="TEST-001",
            price_amount=Decimal("99.99"),
            price_currency="BRL",
            quantity=10,
            category="electronics",
            tags=["new", "featured"],
            created_by="test-user",
        )
        
        assert command.name == "Test Item"
        assert command.sku == "TEST-001"
        assert command.price_amount == Decimal("99.99")
        assert command.quantity == 10
        assert command.command_type == "CreateItemCommand"

    def test_update_item_command_structure(self) -> None:
        """Test UpdateItemCommand has correct structure."""
        from application.examples.item.commands import UpdateItemCommand
        
        command = UpdateItemCommand(
            item_id="item-123",
            name="Updated Item",
            price_amount=Decimal("149.99"),
            updated_by="test-user",
        )
        
        assert command.item_id == "item-123"
        assert command.name == "Updated Item"
        assert command.price_amount == Decimal("149.99")

    def test_delete_item_command_structure(self) -> None:
        """Test DeleteItemCommand has correct structure."""
        from application.examples.item.commands import DeleteItemCommand
        
        command = DeleteItemCommand(
            item_id="item-123",
            deleted_by="test-user",
        )
        
        assert command.item_id == "item-123"
        assert command.deleted_by == "test-user"


class TestItemExampleQueries:
    """Integration tests for ItemExample query operations."""

    def test_get_item_query_structure(self) -> None:
        """Test GetItemQuery has correct structure."""
        from application.examples.item.queries import GetItemQuery
        
        query = GetItemQuery(item_id="item-123")
        
        assert query.item_id == "item-123"
        assert query.query_type == "GetItemQuery"

    def test_list_items_query_structure(self) -> None:
        """Test ListItemsQuery has correct structure."""
        from application.examples.item.queries import ListItemsQuery
        
        query = ListItemsQuery(
            page=2,
            size=50,
            category="electronics",
            status="active",
        )
        
        assert query.page == 2
        assert query.size == 50
        assert query.category == "electronics"
        assert query.status == "active"


class TestItemExampleMapper:
    """Integration tests for ItemExample mapper."""

    def test_mapper_implements_imapper(self) -> None:
        """Test ItemExampleMapper implements IMapper interface."""
        from application.examples.item.mapper import ItemExampleMapper
        
        mapper = ItemExampleMapper()
        
        # Verify IMapper interface methods exist
        assert hasattr(mapper, "to_dto")
        assert hasattr(mapper, "to_entity")
        assert hasattr(mapper, "to_dto_list")
        assert hasattr(mapper, "to_entity_list")
        assert callable(mapper.to_dto)
        assert callable(mapper.to_entity)

    def test_mapper_backward_compatibility(self) -> None:
        """Test mapper static methods for backward compatibility."""
        from application.examples.item.mapper import ItemExampleMapper
        
        # Verify static methods exist for backward compatibility
        assert hasattr(ItemExampleMapper, "to_response")
        assert hasattr(ItemExampleMapper, "to_response_list")
        assert callable(ItemExampleMapper.to_response)
        assert callable(ItemExampleMapper.to_response_list)


class TestItemExampleErrorHandling:
    """Integration tests for error handling."""

    def test_not_found_error_structure(self) -> None:
        """Test NotFoundError has correct structure."""
        from application.examples.shared.errors import NotFoundError
        
        error = NotFoundError("ItemExample", "item-123")
        
        assert error.entity_type == "ItemExample"
        assert error.entity_id == "item-123"
        assert "entity_type" in error.details
        assert "entity_id" in error.details

    def test_validation_error_structure(self) -> None:
        """Test ValidationError has correct structure."""
        from application.examples.shared.errors import ValidationError
        
        error = ValidationError("Invalid SKU format", field="sku")
        
        assert error.message == "Invalid SKU format"
        assert error.field == "sku"
        assert len(error.errors) == 1
        assert error.errors[0]["field"] == "sku"
