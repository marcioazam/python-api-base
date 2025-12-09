"""Unit tests for pedido example handlers.

**Feature: test-coverage-80-percent-v3**
**Validates: Requirements 8.2, 8.3**
"""

from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock

import pytest

from application.examples.pedido.commands import (
    CreatePedidoCommand,
    AddItemToPedidoCommand,
    ConfirmPedidoCommand,
    CancelPedidoCommand,
)
from application.examples.pedido.handlers import (
    CreatePedidoCommandHandler,
    GetPedidoQueryHandler,
    ListPedidosQueryHandler,
)
from application.examples.pedido.queries import GetPedidoQuery, ListPedidosQuery
from domain.examples.item.entity import ItemExample, Money
from domain.examples.pedido.entity import PedidoExample, PedidoStatus


class MockPedidoRepository:
    """Mock repository for pedido testing."""

    def __init__(self) -> None:
        self._pedidos: dict[str, PedidoExample] = {}

    async def get(self, pedido_id: str) -> PedidoExample | None:
        return self._pedidos.get(pedido_id)

    async def create(self, entity: PedidoExample) -> PedidoExample:
        self._pedidos[entity.id] = entity
        return entity

    async def update(self, entity: PedidoExample) -> PedidoExample:
        self._pedidos[entity.id] = entity
        return entity

    async def get_all(self, **kwargs: Any) -> list[PedidoExample]:
        return list(self._pedidos.values())

    async def count(self, **kwargs: Any) -> int:
        return len(self._pedidos)

    def add_pedido(self, pedido: PedidoExample) -> None:
        """Helper to add pedido directly for testing."""
        self._pedidos[pedido.id] = pedido


class MockItemRepository:
    """Mock repository for item testing."""

    def __init__(self) -> None:
        self._items: dict[str, ItemExample] = {}

    async def get(self, item_id: str) -> ItemExample | None:
        return self._items.get(item_id)

    def add_item(self, item: ItemExample) -> None:
        """Helper to add item directly for testing."""
        self._items[item.id] = item


class TestGetPedidoQueryHandler:
    """Tests for GetPedidoQueryHandler."""

    @pytest.fixture
    def repository(self) -> MockPedidoRepository:
        """Create mock repository."""
        return MockPedidoRepository()

    @pytest.fixture
    def handler(self, repository: MockPedidoRepository) -> GetPedidoQueryHandler:
        """Create handler with mock repository."""
        return GetPedidoQueryHandler(repository=repository)

    @pytest.fixture
    def existing_pedido(self, repository: MockPedidoRepository) -> PedidoExample:
        """Create existing pedido in repository."""
        pedido = PedidoExample.create(
            customer_id="cust-001",
            customer_name="Test Customer",
            customer_email="test@example.com",
        )
        repository.add_pedido(pedido)
        return pedido

    @pytest.mark.asyncio
    async def test_get_pedido_success(
        self,
        handler: GetPedidoQueryHandler,
        existing_pedido: PedidoExample,
    ) -> None:
        """Test successful pedido retrieval."""
        query = GetPedidoQuery(pedido_id=existing_pedido.id)

        result = await handler.handle(query)

        assert result.is_ok()
        response = result.unwrap()
        assert response.customer_name == "Test Customer"


    @pytest.mark.asyncio
    async def test_get_nonexistent_pedido_fails(
        self, handler: GetPedidoQueryHandler
    ) -> None:
        """Test getting non-existent pedido fails."""
        query = GetPedidoQuery(pedido_id="nonexistent-id")

        result = await handler.handle(query)

        assert result.is_err()


class TestListPedidosQueryHandler:
    """Tests for ListPedidosQueryHandler."""

    @pytest.fixture
    def repository(self) -> MockPedidoRepository:
        """Create mock repository."""
        return MockPedidoRepository()

    @pytest.fixture
    def handler(self, repository: MockPedidoRepository) -> ListPedidosQueryHandler:
        """Create handler with mock repository."""
        return ListPedidosQueryHandler(repository=repository)

    @pytest.mark.asyncio
    async def test_list_pedidos_empty(self, handler: ListPedidosQueryHandler) -> None:
        """Test listing pedidos when empty."""
        query = ListPedidosQuery(page=1, size=10)

        result = await handler.handle(query)

        assert result.is_ok()
        response = result.unwrap()
        assert response.total == 0
        assert len(response.items) == 0

    @pytest.mark.asyncio
    async def test_list_pedidos_with_data(
        self, handler: ListPedidosQueryHandler, repository: MockPedidoRepository
    ) -> None:
        """Test listing pedidos with data."""
        for i in range(3):
            pedido = PedidoExample.create(
                customer_id=f"cust-{i:03d}",
                customer_name=f"Customer {i}",
                customer_email=f"customer{i}@example.com",
            )
            repository.add_pedido(pedido)

        query = ListPedidosQuery(page=1, size=10)

        result = await handler.handle(query)

        assert result.is_ok()
        response = result.unwrap()
        assert response.total == 3
        assert len(response.items) == 3


class TestCreatePedidoCommandHandler:
    """Tests for CreatePedidoCommandHandler."""

    @pytest.fixture
    def pedido_repository(self) -> MockPedidoRepository:
        """Create mock pedido repository."""
        return MockPedidoRepository()

    @pytest.fixture
    def item_repository(self) -> MockItemRepository:
        """Create mock item repository."""
        return MockItemRepository()

    @pytest.fixture
    def event_bus(self) -> AsyncMock:
        """Create mock event bus."""
        return AsyncMock()

    @pytest.fixture
    def handler(
        self,
        pedido_repository: MockPedidoRepository,
        item_repository: MockItemRepository,
        event_bus: AsyncMock,
    ) -> CreatePedidoCommandHandler:
        """Create handler with mocks."""
        return CreatePedidoCommandHandler(
            pedido_repository=pedido_repository,
            item_repository=item_repository,
            event_bus=event_bus,
        )

    @pytest.fixture
    def available_item(self, item_repository: MockItemRepository) -> ItemExample:
        """Create available item in repository."""
        item = ItemExample.create(
            name="Test Item",
            description="Test Description",
            price=Money(Decimal("100.00")),
            sku="TEST-001",
            quantity=10,
        )
        item_repository.add_item(item)
        return item

    @pytest.mark.asyncio
    async def test_create_pedido_success(
        self,
        handler: CreatePedidoCommandHandler,
        available_item: ItemExample,
    ) -> None:
        """Test successful pedido creation."""
        command = CreatePedidoCommand(
            customer_id="cust-001",
            customer_name="Test Customer",
            customer_email="test@example.com",
            items=[{"item_id": available_item.id, "quantity": 2}],
        )

        result = await handler.handle(command)

        assert result.is_ok()
        response = result.unwrap()
        assert response.customer_name == "Test Customer"

    @pytest.mark.asyncio
    async def test_create_pedido_item_not_found(
        self,
        handler: CreatePedidoCommandHandler,
    ) -> None:
        """Test pedido creation fails when item not found."""
        command = CreatePedidoCommand(
            customer_id="cust-001",
            customer_name="Test Customer",
            customer_email="test@example.com",
            items=[{"item_id": "nonexistent", "quantity": 1}],
        )

        result = await handler.handle(command)

        assert result.is_err()

    @pytest.mark.asyncio
    async def test_create_pedido_item_unavailable(
        self,
        handler: CreatePedidoCommandHandler,
        item_repository: MockItemRepository,
    ) -> None:
        """Test pedido creation fails when item unavailable."""
        item = ItemExample.create(
            name="Unavailable Item",
            description="Out of stock",
            price=Money(Decimal("50.00")),
            sku="OUT-001",
            quantity=0,
        )
        item_repository.add_item(item)

        command = CreatePedidoCommand(
            customer_id="cust-001",
            customer_name="Test Customer",
            customer_email="test@example.com",
            items=[{"item_id": item.id, "quantity": 1}],
        )

        result = await handler.handle(command)

        assert result.is_err()


class TestAddItemToPedidoCommandHandler:
    """Tests for AddItemToPedidoCommandHandler."""

    @pytest.fixture
    def pedido_repository(self) -> MockPedidoRepository:
        """Create mock pedido repository."""
        return MockPedidoRepository()

    @pytest.fixture
    def item_repository(self) -> MockItemRepository:
        """Create mock item repository."""
        return MockItemRepository()

    @pytest.fixture
    def handler(
        self,
        pedido_repository: MockPedidoRepository,
        item_repository: MockItemRepository,
    ) -> "AddItemToPedidoCommandHandler":
        """Create handler with mocks."""
        from application.examples.pedido.handlers import AddItemToPedidoCommandHandler
        return AddItemToPedidoCommandHandler(
            pedido_repository=pedido_repository,
            item_repository=item_repository,
        )

    @pytest.fixture
    def existing_pedido(self, pedido_repository: MockPedidoRepository) -> PedidoExample:
        """Create existing pedido."""
        pedido = PedidoExample.create(
            customer_id="cust-001",
            customer_name="Test Customer",
            customer_email="test@example.com",
        )
        pedido_repository.add_pedido(pedido)
        return pedido

    @pytest.fixture
    def available_item(self, item_repository: MockItemRepository) -> ItemExample:
        """Create available item."""
        item = ItemExample.create(
            name="Test Item",
            description="Test",
            price=Money(Decimal("50.00")),
            sku="TEST-002",
            quantity=5,
        )
        item_repository.add_item(item)
        return item

    @pytest.mark.asyncio
    async def test_add_item_success(
        self,
        handler: "AddItemToPedidoCommandHandler",
        existing_pedido: PedidoExample,
        available_item: ItemExample,
    ) -> None:
        """Test adding item to pedido."""
        command = AddItemToPedidoCommand(
            pedido_id=existing_pedido.id,
            item_id=available_item.id,
            quantity=2,
        )

        result = await handler.handle(command)

        assert result.is_ok()

    @pytest.mark.asyncio
    async def test_add_item_pedido_not_found(
        self,
        handler: "AddItemToPedidoCommandHandler",
        available_item: ItemExample,
    ) -> None:
        """Test adding item fails when pedido not found."""
        command = AddItemToPedidoCommand(
            pedido_id="nonexistent",
            item_id=available_item.id,
            quantity=1,
        )

        result = await handler.handle(command)

        assert result.is_err()

    @pytest.mark.asyncio
    async def test_add_item_item_not_found(
        self,
        handler: "AddItemToPedidoCommandHandler",
        existing_pedido: PedidoExample,
    ) -> None:
        """Test adding item fails when item not found."""
        command = AddItemToPedidoCommand(
            pedido_id=existing_pedido.id,
            item_id="nonexistent",
            quantity=1,
        )

        result = await handler.handle(command)

        assert result.is_err()


class TestConfirmPedidoCommandHandler:
    """Tests for ConfirmPedidoCommandHandler."""

    @pytest.fixture
    def repository(self) -> MockPedidoRepository:
        """Create mock repository."""
        return MockPedidoRepository()

    @pytest.fixture
    def handler(self, repository: MockPedidoRepository) -> "ConfirmPedidoCommandHandler":
        """Create handler."""
        from application.examples.pedido.handlers import ConfirmPedidoCommandHandler
        return ConfirmPedidoCommandHandler(repository=repository)

    @pytest.fixture
    def pedido_with_items(self, repository: MockPedidoRepository) -> PedidoExample:
        """Create pedido with items."""
        pedido = PedidoExample.create(
            customer_id="cust-001",
            customer_name="Test Customer",
            customer_email="test@example.com",
        )
        pedido.add_item(
            item_id="item-001",
            item_name="Test Item",
            quantity=1,
            unit_price=Money(Decimal("100.00")),
        )
        repository.add_pedido(pedido)
        return pedido

    @pytest.mark.asyncio
    async def test_confirm_pedido_success(
        self,
        handler: "ConfirmPedidoCommandHandler",
        pedido_with_items: PedidoExample,
    ) -> None:
        """Test confirming pedido."""
        command = ConfirmPedidoCommand(
            pedido_id=pedido_with_items.id,
            confirmed_by="admin",
        )

        result = await handler.handle(command)

        assert result.is_ok()
        response = result.unwrap()
        assert response.status == PedidoStatus.CONFIRMED.value

    @pytest.mark.asyncio
    async def test_confirm_pedido_not_found(
        self,
        handler: "ConfirmPedidoCommandHandler",
    ) -> None:
        """Test confirming non-existent pedido fails."""
        command = ConfirmPedidoCommand(
            pedido_id="nonexistent",
            confirmed_by="admin",
        )

        result = await handler.handle(command)

        assert result.is_err()


class TestCancelPedidoCommandHandler:
    """Tests for CancelPedidoCommandHandler."""

    @pytest.fixture
    def repository(self) -> MockPedidoRepository:
        """Create mock repository."""
        return MockPedidoRepository()

    @pytest.fixture
    def handler(self, repository: MockPedidoRepository) -> "CancelPedidoCommandHandler":
        """Create handler."""
        from application.examples.pedido.handlers import CancelPedidoCommandHandler
        return CancelPedidoCommandHandler(repository=repository)

    @pytest.fixture
    def pending_pedido(self, repository: MockPedidoRepository) -> PedidoExample:
        """Create pending pedido."""
        pedido = PedidoExample.create(
            customer_id="cust-001",
            customer_name="Test Customer",
            customer_email="test@example.com",
        )
        repository.add_pedido(pedido)
        return pedido

    @pytest.mark.asyncio
    async def test_cancel_pedido_success(
        self,
        handler: "CancelPedidoCommandHandler",
        pending_pedido: PedidoExample,
    ) -> None:
        """Test cancelling pedido."""
        command = CancelPedidoCommand(
            pedido_id=pending_pedido.id,
            reason="Customer request",
            cancelled_by="admin",
        )

        result = await handler.handle(command)

        assert result.is_ok()
        response = result.unwrap()
        assert response.status == PedidoStatus.CANCELLED.value

    @pytest.mark.asyncio
    async def test_cancel_pedido_not_found(
        self,
        handler: "CancelPedidoCommandHandler",
    ) -> None:
        """Test cancelling non-existent pedido fails."""
        command = CancelPedidoCommand(
            pedido_id="nonexistent",
            reason="Test",
            cancelled_by="admin",
        )

        result = await handler.handle(command)

        assert result.is_err()
