"""Unit tests for PlaceOrderUseCase.

Demonstrates testing a complex UseCase with mocked dependencies.

**Feature: architecture-consolidation-2025**
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from application.examples.order.dtos import (
    OrderItemInput,
    PlaceOrderInput,
)
from application.examples.order.use_cases.place_order import PlaceOrderUseCase


@pytest.fixture
def mock_catalog() -> AsyncMock:
    """Create mock item catalog."""
    catalog = AsyncMock()
    catalog.get_item = AsyncMock(
        return_value={
            "id": "item-1",
            "name": "Test Item",
            "price": "29.90",
        }
    )
    catalog.check_availability = AsyncMock(return_value=True)
    return catalog


@pytest.fixture
def mock_inventory() -> AsyncMock:
    """Create mock inventory service."""
    inventory = AsyncMock()
    inventory.reserve_items = AsyncMock(return_value=True)
    inventory.release_items = AsyncMock()
    return inventory


@pytest.fixture
def mock_payment() -> AsyncMock:
    """Create mock payment service."""
    payment = AsyncMock()
    payment.process_payment = AsyncMock(
        return_value={"payment_id": "pay-123", "status": "approved"}
    )
    payment.refund_payment = AsyncMock(return_value=True)
    return payment


@pytest.fixture
def mock_orders() -> AsyncMock:
    """Create mock order repository."""
    orders = AsyncMock()
    orders.create = AsyncMock(return_value={"id": "order-123"})
    return orders


@pytest.fixture
def mock_notifications() -> AsyncMock:
    """Create mock notification service."""
    notifications = AsyncMock()
    notifications.send_order_confirmation = AsyncMock()
    return notifications


@pytest.fixture
def use_case(
    mock_catalog: AsyncMock,
    mock_inventory: AsyncMock,
    mock_payment: AsyncMock,
    mock_orders: AsyncMock,
    mock_notifications: AsyncMock,
) -> PlaceOrderUseCase:
    """Create PlaceOrderUseCase with mocked dependencies."""
    return PlaceOrderUseCase(
        item_catalog=mock_catalog,
        inventory_service=mock_inventory,
        payment_service=mock_payment,
        order_repository=mock_orders,
        notification_service=mock_notifications,
    )


@pytest.fixture
def valid_input() -> PlaceOrderInput:
    """Create valid order input."""
    return PlaceOrderInput(
        customer_id="cust-123",
        items=[OrderItemInput(item_id="item-1", quantity=2)],
        shipping_address="123 Main St, City, Country",
        payment_method="credit_card",
    )


class TestPlaceOrderUseCaseSuccess:
    """Tests for successful order placement."""

    @pytest.mark.asyncio
    async def test_place_order_success(
        self,
        use_case: PlaceOrderUseCase,
        valid_input: PlaceOrderInput,
        mock_catalog: AsyncMock,
        mock_inventory: AsyncMock,
        mock_payment: AsyncMock,
        mock_orders: AsyncMock,
        mock_notifications: AsyncMock,
    ) -> None:
        """Successfully place an order."""
        result = await use_case.execute(valid_input)

        assert result.is_ok()
        output = result.unwrap()

        # Verify output
        assert output.customer_id == "cust-123"
        assert output.status == "confirmed"
        assert len(output.items) == 1
        assert output.items[0].item_name == "Test Item"
        assert output.items[0].quantity == 2
        assert output.shipping_cost == Decimal("9.90")

        # Verify all services were called
        mock_catalog.get_item.assert_called_once_with("item-1")
        mock_catalog.check_availability.assert_called_once_with("item-1", 2)
        mock_inventory.reserve_items.assert_called_once()
        mock_payment.process_payment.assert_called_once()
        mock_orders.create.assert_called_once()
        mock_notifications.send_order_confirmation.assert_called_once()

    @pytest.mark.asyncio
    async def test_place_order_calculates_total_correctly(
        self,
        use_case: PlaceOrderUseCase,
        valid_input: PlaceOrderInput,
        mock_catalog: AsyncMock,
    ) -> None:
        """Order total is calculated correctly."""
        mock_catalog.get_item.return_value = {
            "id": "item-1",
            "name": "Test Item",
            "price": "50.00",
        }

        result = await use_case.execute(valid_input)

        assert result.is_ok()
        output = result.unwrap()

        # 2 items * 50.00 = 100.00 subtotal
        assert output.subtotal == Decimal("100.00")
        # 100.00 + 9.90 shipping = 109.90 total
        assert output.total == Decimal("109.90")


class TestPlaceOrderUseCaseValidation:
    """Tests for input validation."""

    @pytest.mark.asyncio
    async def test_empty_customer_id_fails(
        self, use_case: PlaceOrderUseCase
    ) -> None:
        """Order with empty customer ID fails validation."""
        input_data = PlaceOrderInput(
            customer_id="",
            items=[OrderItemInput(item_id="item-1", quantity=1)],
            shipping_address="123 Main St",
        )

        result = await use_case.execute(input_data)

        assert result.is_err()
        error = result.error  # type: ignore[union-attr]
        assert error.code == "VALIDATION_ERROR"
        assert "customer_id" in error.details.get("field", "")

    @pytest.mark.asyncio
    async def test_empty_items_fails(
        self, use_case: PlaceOrderUseCase
    ) -> None:
        """Order with no items fails validation."""
        input_data = PlaceOrderInput(
            customer_id="cust-123",
            items=[],
            shipping_address="123 Main St",
        )

        result = await use_case.execute(input_data)

        assert result.is_err()
        error = result.error  # type: ignore[union-attr]
        assert error.code == "VALIDATION_ERROR"

    @pytest.mark.asyncio
    async def test_zero_quantity_fails(
        self, use_case: PlaceOrderUseCase
    ) -> None:
        """Order with zero quantity item fails validation."""
        input_data = PlaceOrderInput(
            customer_id="cust-123",
            items=[OrderItemInput(item_id="item-1", quantity=0)],
            shipping_address="123 Main St",
        )

        result = await use_case.execute(input_data)

        assert result.is_err()
        error = result.error  # type: ignore[union-attr]
        assert error.code == "VALIDATION_ERROR"


class TestPlaceOrderUseCaseBusinessRules:
    """Tests for business rule enforcement."""

    @pytest.mark.asyncio
    async def test_item_not_found_fails(
        self,
        use_case: PlaceOrderUseCase,
        valid_input: PlaceOrderInput,
        mock_catalog: AsyncMock,
    ) -> None:
        """Order with non-existent item fails."""
        mock_catalog.get_item.return_value = None

        result = await use_case.execute(valid_input)

        assert result.is_err()
        error = result.error  # type: ignore[union-attr]
        assert error.code == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_item_not_available_fails(
        self,
        use_case: PlaceOrderUseCase,
        valid_input: PlaceOrderInput,
        mock_catalog: AsyncMock,
    ) -> None:
        """Order with unavailable item fails."""
        mock_catalog.check_availability.return_value = False

        result = await use_case.execute(valid_input)

        assert result.is_err()
        error = result.error  # type: ignore[union-attr]
        assert error.code == "BUSINESS_RULE_VIOLATION"
        assert error.details.get("rule") == "ITEM_AVAILABILITY"

    @pytest.mark.asyncio
    async def test_below_minimum_order_fails(
        self,
        use_case: PlaceOrderUseCase,
        mock_catalog: AsyncMock,
    ) -> None:
        """Order below minimum amount fails."""
        mock_catalog.get_item.return_value = {
            "id": "item-1",
            "name": "Cheap Item",
            "price": "1.00",  # 1 * 1.00 = 1.00 < 10.00 minimum
        }

        input_data = PlaceOrderInput(
            customer_id="cust-123",
            items=[OrderItemInput(item_id="item-1", quantity=1)],
            shipping_address="123 Main St",
        )

        result = await use_case.execute(input_data)

        assert result.is_err()
        error = result.error  # type: ignore[union-attr]
        assert error.code == "BUSINESS_RULE_VIOLATION"
        assert error.details.get("rule") == "MIN_ORDER_AMOUNT"


class TestPlaceOrderUseCaseRollback:
    """Tests for rollback/compensation on failure."""

    @pytest.mark.asyncio
    async def test_payment_failure_releases_inventory(
        self,
        use_case: PlaceOrderUseCase,
        valid_input: PlaceOrderInput,
        mock_payment: AsyncMock,
        mock_inventory: AsyncMock,
    ) -> None:
        """Payment failure triggers inventory release."""
        mock_payment.process_payment.return_value = None  # Payment declined

        result = await use_case.execute(valid_input)

        assert result.is_err()
        # Verify inventory was released
        mock_inventory.release_items.assert_called_once()

    @pytest.mark.asyncio
    async def test_order_creation_failure_refunds_and_releases(
        self,
        use_case: PlaceOrderUseCase,
        valid_input: PlaceOrderInput,
        mock_orders: AsyncMock,
        mock_payment: AsyncMock,
        mock_inventory: AsyncMock,
    ) -> None:
        """Order creation failure triggers refund and inventory release."""
        mock_orders.create.side_effect = Exception("Database error")

        result = await use_case.execute(valid_input)

        assert result.is_err()
        # Verify rollback actions
        mock_payment.refund_payment.assert_called_once()
        mock_inventory.release_items.assert_called_once()
