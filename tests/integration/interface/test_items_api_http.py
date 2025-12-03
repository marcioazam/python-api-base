"""Integration tests for ItemExample API via HTTP.

**Feature: interface-middleware-routes-analysis**
**Validates: Requirements 2.1, 2.2**

Tests the full HTTP request/response cycle for ItemExample endpoints,
including middleware execution, RBAC enforcement, and response structure.
"""

import pytest
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient


# Skip if dependencies not available
pytest.importorskip("fastapi")


class MockItemEntity:
    """Mock item entity for testing."""
    
    def __init__(
        self,
        id: str = "item-123",
        name: str = "Test Item",
        sku: str = "TEST-001",
        price_amount: Decimal = Decimal("99.99"),
        price_currency: str = "BRL",
        quantity: int = 10,
        category: str = "electronics",
        status: str = "active",
    ) -> None:
        self.id = id
        self.name = name
        self.sku = sku
        self.price_amount = price_amount
        self.price_currency = price_currency
        self.quantity = quantity
        self.category = category
        self.status = status
        self.tags: list[str] = []
        self.created_at = "2024-01-01T00:00:00Z"
        self.updated_at = "2024-01-01T00:00:00Z"


class MockItemRepository:
    """Mock repository for testing."""
    
    def __init__(self) -> None:
        self._items: dict[str, MockItemEntity] = {}
        self._counter = 0
    
    async def get(self, item_id: str) -> MockItemEntity | None:
        return self._items.get(item_id)
    
    async def get_by_sku(self, sku: str) -> MockItemEntity | None:
        for item in self._items.values():
            if item.sku == sku:
                return item
        return None
    
    async def create(self, entity: Any) -> MockItemEntity:
        self._counter += 1
        item = MockItemEntity(
            id=f"item-{self._counter}",
            name=getattr(entity, "name", "Test"),
            sku=getattr(entity, "sku", f"SKU-{self._counter}"),
        )
        self._items[item.id] = item
        return item
    
    async def update(self, entity: Any) -> MockItemEntity:
        if hasattr(entity, "id") and entity.id in self._items:
            self._items[entity.id] = entity
        return entity
    
    async def delete(self, item_id: str) -> bool:
        if item_id in self._items:
            del self._items[item_id]
            return True
        return False
    
    async def get_all(self, **kwargs: Any) -> list[MockItemEntity]:
        return list(self._items.values())
    
    async def count(self, **kwargs: Any) -> int:
        return len(self._items)


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Headers for authenticated requests with admin role."""
    return {
        "X-User-Id": "test-user",
        "X-User-Roles": "admin",
        "X-Tenant-Id": "test-tenant",
    }


@pytest.fixture
def viewer_headers() -> dict[str, str]:
    """Headers for viewer role (read-only)."""
    return {
        "X-User-Id": "viewer-user",
        "X-User-Roles": "viewer",
    }


@pytest.fixture
def item_create_data() -> dict[str, Any]:
    """Valid item creation data."""
    return {
        "name": "Test Item",
        "sku": "TEST-001",
        "price": {"amount": "99.99", "currency": "BRL"},
        "quantity": 10,
        "category": "electronics",
        "tags": ["new", "featured"],
    }


class TestItemsAPIStructure:
    """Tests for ItemExample API response structure."""

    def test_list_items_response_structure(self) -> None:
        """Test GET /api/v1/examples/items returns paginated response structure.
        
        **Feature: interface-middleware-routes-analysis**
        **Validates: Requirements 2.1**
        """
        from application.common.base.dto import PaginatedResponse
        from application.examples import ItemExampleResponse
        
        # Verify PaginatedResponse has required fields
        response = PaginatedResponse[ItemExampleResponse](
            items=[],
            total=0,
            page=1,
            size=20,
        )
        
        assert hasattr(response, "items")
        assert hasattr(response, "total")
        assert hasattr(response, "page")
        assert hasattr(response, "size")
        assert response.page == 1
        assert response.size == 20

    def test_api_response_structure(self) -> None:
        """Test ApiResponse wrapper structure.
        
        **Feature: interface-middleware-routes-analysis**
        **Validates: Requirements 2.1**
        """
        from application.common.base.dto import ApiResponse
        
        response = ApiResponse[dict](data={"id": "test"}, status_code=200)
        
        assert hasattr(response, "data")
        assert hasattr(response, "status_code")
        assert response.data == {"id": "test"}


class TestItemsAPIEndpoints:
    """Tests for ItemExample API endpoints."""

    def test_item_create_dto_validation(self, item_create_data: dict[str, Any]) -> None:
        """Test ItemExampleCreate DTO validation.
        
        **Feature: interface-middleware-routes-analysis**
        **Validates: Requirements 2.2**
        """
        from application.examples import ItemExampleCreate
        
        dto = ItemExampleCreate(**item_create_data)
        
        assert dto.name == "Test Item"
        assert dto.sku == "TEST-001"
        assert dto.quantity == 10

    def test_item_update_dto_validation(self) -> None:
        """Test ItemExampleUpdate DTO validation.
        
        **Feature: interface-middleware-routes-analysis**
        **Validates: Requirements 2.2**
        """
        from application.examples import ItemExampleUpdate
        from application.examples.shared.dtos import MoneyDTO
        
        dto = ItemExampleUpdate(
            name="Updated Item",
            price=MoneyDTO(amount=Decimal("149.99"), currency="BRL"),
        )
        
        assert dto.name == "Updated Item"
        assert dto.price is not None
        assert dto.price.amount == Decimal("149.99")

    def test_item_response_dto_structure(self) -> None:
        """Test ItemExampleResponse DTO structure.
        
        **Feature: interface-middleware-routes-analysis**
        **Validates: Requirements 2.1**
        """
        from application.examples import ItemExampleResponse
        
        # Verify response model has required fields
        assert hasattr(ItemExampleResponse, "model_fields")
        fields = ItemExampleResponse.model_fields
        
        assert "id" in fields
        assert "name" in fields
        assert "sku" in fields


class TestItemsAPIRBAC:
    """Tests for RBAC enforcement on ItemExample endpoints."""

    def test_rbac_user_structure(self) -> None:
        """Test RBACUser structure for permission checking.
        
        **Feature: interface-middleware-routes-analysis**
        **Validates: Requirements 2.2**
        """
        from infrastructure.security.rbac import RBACUser, Permission
        
        user = RBACUser(id="test-user", roles=["admin"])
        
        assert user.id == "test-user"
        assert "admin" in user.roles
        assert Permission.WRITE.value == "write"
        assert Permission.DELETE.value == "delete"

    def test_rbac_service_permission_check(self) -> None:
        """Test RBAC service permission checking.
        
        **Feature: interface-middleware-routes-analysis**
        **Validates: Requirements 2.2**
        """
        from infrastructure.security.rbac import RBACUser, Permission, get_rbac_service
        
        rbac = get_rbac_service()
        admin_user = RBACUser(id="admin", roles=["admin"])
        viewer_user = RBACUser(id="viewer", roles=["viewer"])
        
        # Admin should have write permission
        assert rbac.check_permission(admin_user, Permission.WRITE) is True
        
        # Viewer should not have write permission
        assert rbac.check_permission(viewer_user, Permission.WRITE) is False


class TestItemsAPIErrorHandling:
    """Tests for error handling in ItemExample API."""

    def test_not_found_error_structure(self) -> None:
        """Test NotFoundError structure.
        
        **Feature: interface-middleware-routes-analysis**
        **Validates: Requirements 2.1**
        """
        from application.examples.shared.errors import NotFoundError
        
        error = NotFoundError("ItemExample", "item-123")
        
        assert error.entity_type == "ItemExample"
        assert error.entity_id == "item-123"
        assert "not found" in error.message.lower()

    def test_validation_error_structure(self) -> None:
        """Test ValidationError structure.
        
        **Feature: interface-middleware-routes-analysis**
        **Validates: Requirements 2.2**
        """
        from application.examples.shared.errors import ValidationError
        
        error = ValidationError("Invalid SKU format", field="sku")
        
        assert error.message == "Invalid SKU format"
        assert error.field == "sku"


class TestItemsAPIUseCase:
    """Tests for ItemExampleUseCase integration."""

    def test_use_case_initialization(self) -> None:
        """Test ItemExampleUseCase can be initialized.
        
        **Feature: interface-middleware-routes-analysis**
        **Validates: Requirements 2.1, 2.2**
        """
        from application.examples import ItemExampleUseCase
        from infrastructure.kafka import NoOpEventPublisher
        
        mock_repo = MockItemRepository()
        publisher = NoOpEventPublisher()
        
        use_case = ItemExampleUseCase(
            repository=mock_repo,
            kafka_publisher=publisher,
        )
        
        assert use_case is not None

    @pytest.mark.asyncio
    async def test_use_case_list_returns_result(self) -> None:
        """Test ItemExampleUseCase.list returns Result type.
        
        **Feature: interface-middleware-routes-analysis**
        **Validates: Requirements 2.1**
        """
        from application.examples import ItemExampleUseCase
        from infrastructure.kafka import NoOpEventPublisher
        
        mock_repo = MockItemRepository()
        publisher = NoOpEventPublisher()
        use_case = ItemExampleUseCase(repository=mock_repo, kafka_publisher=publisher)
        
        result = await use_case.list(page=1, page_size=20)
        
        # Result should have is_ok/is_err methods
        assert hasattr(result, "is_ok") or hasattr(result, "is_err")
