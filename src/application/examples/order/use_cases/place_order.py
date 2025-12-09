"""PlaceOrderUseCase - Example of a complex business operation.

This UseCase demonstrates:
- Orchestrating multiple services (inventory, payment, notification)
- Enforcing business rules
- Transaction management
- Result-based error handling

**When to use UseCase vs Service:**

- **Service**: CRUD operations on a single entity
  - ItemService.create(), ItemService.update()

- **UseCase**: Complex business operation involving multiple steps/services
  - PlaceOrderUseCase.execute() - validates, checks inventory, processes payment, creates order

**Feature: architecture-consolidation-2025**
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from typing import Any, Protocol
from uuid import uuid4

from application.common.use_cases import BaseUseCase, UseCaseError, UseCaseResult
from application.examples.order.dtos import (
    OrderItemInput,
    OrderItemOutput,
    PlaceOrderInput,
    PlaceOrderOutput,
)
from core.base.patterns.result import Err, Ok
from core.shared.utils.datetime import utc_now

logger = logging.getLogger(__name__)


# =============================================================================
# Protocols for Dependencies (Dependency Inversion)
# =============================================================================


class IItemCatalog(Protocol):
    """Protocol for item catalog service."""

    async def get_item(self, item_id: str) -> dict[str, Any] | None:
        """Get item details by ID."""
        ...

    async def check_availability(self, item_id: str, quantity: int) -> bool:
        """Check if item is available in requested quantity."""
        ...


class IInventoryService(Protocol):
    """Protocol for inventory service."""

    async def reserve_items(
        self, items: list[tuple[str, int]]
    ) -> bool:
        """Reserve items for an order. Returns True if successful."""
        ...

    async def release_items(self, items: list[tuple[str, int]]) -> None:
        """Release reserved items (rollback)."""
        ...


class IPaymentService(Protocol):
    """Protocol for payment service."""

    async def process_payment(
        self,
        customer_id: str,
        amount: Decimal,
        payment_method: str,
    ) -> dict[str, Any] | None:
        """Process payment. Returns payment details or None if failed."""
        ...

    async def refund_payment(self, payment_id: str) -> bool:
        """Refund a payment."""
        ...


class IOrderRepository(Protocol):
    """Protocol for order repository."""

    async def create(self, order_data: dict[str, Any]) -> dict[str, Any]:
        """Create a new order."""
        ...


class INotificationService(Protocol):
    """Protocol for notification service."""

    async def send_order_confirmation(
        self, customer_id: str, order_id: str
    ) -> None:
        """Send order confirmation notification."""
        ...


# =============================================================================
# PlaceOrderUseCase
# =============================================================================


class PlaceOrderUseCase(BaseUseCase[PlaceOrderInput, PlaceOrderOutput]):
    """Use case for placing an order.

    This is a complex business operation that:
    1. Validates the order input
    2. Checks item availability in catalog
    3. Reserves inventory
    4. Processes payment
    5. Creates the order
    6. Sends confirmation notification

    If any step fails, previous steps are rolled back (compensating transactions).

    Example:
        >>> use_case = PlaceOrderUseCase(
        ...     item_catalog=catalog,
        ...     inventory_service=inventory,
        ...     payment_service=payment,
        ...     order_repository=orders,
        ...     notification_service=notifications,
        ... )
        >>> result = await use_case.execute(PlaceOrderInput(
        ...     customer_id="cust-123",
        ...     items=[OrderItemInput(item_id="item-1", quantity=2)],
        ...     shipping_address="123 Main St",
        ... ))
        >>> if result.is_ok():
        ...     order = result.unwrap()
        ...     print(f"Order {order.order_id} placed successfully!")

    **Feature: architecture-consolidation-2025**
    """

    # Business rules constants
    MIN_ORDER_AMOUNT = Decimal("10.00")
    MAX_ITEMS_PER_ORDER = 50
    SHIPPING_COST = Decimal("9.90")
    DELIVERY_DAYS = 5

    def __init__(
        self,
        item_catalog: IItemCatalog,
        inventory_service: IInventoryService,
        payment_service: IPaymentService,
        order_repository: IOrderRepository,
        notification_service: INotificationService | None = None,
    ) -> None:
        """Initialize PlaceOrderUseCase.

        Args:
            item_catalog: Service to get item details and check availability.
            inventory_service: Service to reserve/release inventory.
            payment_service: Service to process payments.
            order_repository: Repository to persist orders.
            notification_service: Optional service to send notifications.
        """
        super().__init__()
        self._catalog = item_catalog
        self._inventory = inventory_service
        self._payment = payment_service
        self._orders = order_repository
        self._notifications = notification_service

    async def execute(
        self, input: PlaceOrderInput
    ) -> UseCaseResult[PlaceOrderOutput]:
        """Execute the place order use case.

        Steps:
        1. Validate input
        2. Fetch and validate items from catalog
        3. Reserve inventory
        4. Process payment
        5. Create order
        6. Send notification (async, non-blocking)

        Args:
            input: Order placement input data.

        Returns:
            Result containing PlaceOrderOutput on success or UseCaseError on failure.
        """
        self._log_start(input)

        # Step 1: Validate input
        validation_result = await self._validate_input(input)
        if validation_result.is_err():
            error = validation_result.error  # type: ignore[union-attr]
            self._log_error(error)
            return Err(error)

        # Step 2: Fetch and validate items
        items_result = await self._fetch_and_validate_items(input.items)
        if items_result.is_err():
            error = items_result.error  # type: ignore[union-attr]
            self._log_error(error)
            return Err(error)

        validated_items = items_result.unwrap()
        subtotal = sum(item.total_price for item in validated_items)
        total = subtotal + self.SHIPPING_COST

        # Step 3: Reserve inventory
        reserve_result = await self._reserve_inventory(input.items)
        if reserve_result.is_err():
            error = reserve_result.error  # type: ignore[union-attr]
            self._log_error(error)
            return Err(error)

        # Step 4: Process payment
        payment_result = await self._process_payment(
            input.customer_id, total, input.payment_method
        )
        if payment_result.is_err():
            # Rollback: release inventory
            await self._rollback_inventory(input.items)
            error = payment_result.error  # type: ignore[union-attr]
            self._log_error(error)
            return Err(error)

        payment_id = payment_result.unwrap()

        # Step 5: Create order
        order_result = await self._create_order(
            input, validated_items, subtotal, total, payment_id
        )
        if order_result.is_err():
            # Rollback: refund payment and release inventory
            await self._payment.refund_payment(payment_id)
            await self._rollback_inventory(input.items)
            error = order_result.error  # type: ignore[union-attr]
            self._log_error(error)
            return Err(error)

        output = order_result.unwrap()

        # Step 6: Send notification (non-blocking)
        await self._send_notification(input.customer_id, output.order_id)

        self._log_success(output)
        return Ok(output)

    # =========================================================================
    # Private Methods - Each step of the use case
    # =========================================================================

    async def _validate_input(
        self, input: PlaceOrderInput
    ) -> UseCaseResult[None]:
        """Validate order input."""
        if not input.customer_id:
            return self._validation_error("Customer ID is required", "customer_id")

        if not input.items:
            return self._validation_error("Order must have at least one item", "items")

        if len(input.items) > self.MAX_ITEMS_PER_ORDER:
            return self._validation_error(
                f"Order cannot have more than {self.MAX_ITEMS_PER_ORDER} items",
                "items",
            )

        if not input.shipping_address:
            return self._validation_error(
                "Shipping address is required", "shipping_address"
            )

        for i, item in enumerate(input.items):
            if item.quantity <= 0:
                return self._validation_error(
                    f"Item {i+1}: quantity must be positive", f"items[{i}].quantity"
                )

        return Ok(None)

    async def _fetch_and_validate_items(
        self, items: list[OrderItemInput]
    ) -> UseCaseResult[list[OrderItemOutput]]:
        """Fetch item details and validate availability."""
        validated_items: list[OrderItemOutput] = []

        for item_input in items:
            # Fetch item from catalog
            item_data = await self._catalog.get_item(item_input.item_id)
            if item_data is None:
                return self._not_found("Item", item_input.item_id)

            # Check availability
            is_available = await self._catalog.check_availability(
                item_input.item_id, item_input.quantity
            )
            if not is_available:
                return self._business_error(
                    f"Item '{item_data.get('name', item_input.item_id)}' is not available "
                    f"in requested quantity ({item_input.quantity})",
                    rule="ITEM_AVAILABILITY",
                )

            # Use provided price or catalog price
            unit_price = item_input.unit_price or Decimal(str(item_data.get("price", 0)))
            total_price = unit_price * item_input.quantity

            validated_items.append(
                OrderItemOutput(
                    item_id=item_input.item_id,
                    item_name=item_data.get("name", "Unknown"),
                    quantity=item_input.quantity,
                    unit_price=unit_price,
                    total_price=total_price,
                )
            )

        # Check minimum order amount
        subtotal = sum(item.total_price for item in validated_items)
        if subtotal < self.MIN_ORDER_AMOUNT:
            return self._business_error(
                f"Order subtotal ({subtotal}) is below minimum ({self.MIN_ORDER_AMOUNT})",
                rule="MIN_ORDER_AMOUNT",
            )

        return Ok(validated_items)

    async def _reserve_inventory(
        self, items: list[OrderItemInput]
    ) -> UseCaseResult[None]:
        """Reserve inventory for order items."""
        items_to_reserve = [(item.item_id, item.quantity) for item in items]

        try:
            success = await self._inventory.reserve_items(items_to_reserve)
            if not success:
                return self._business_error(
                    "Failed to reserve inventory", rule="INVENTORY_RESERVATION"
                )
            return Ok(None)
        except Exception as e:
            self._logger.exception("Inventory reservation failed")
            return Err(
                UseCaseError(
                    message=f"Inventory service error: {e}",
                    code="INVENTORY_ERROR",
                )
            )

    async def _rollback_inventory(self, items: list[OrderItemInput]) -> None:
        """Release reserved inventory (compensating transaction)."""
        items_to_release = [(item.item_id, item.quantity) for item in items]
        try:
            await self._inventory.release_items(items_to_release)
            self._logger.info("Inventory released successfully")
        except Exception:
            self._logger.exception("Failed to release inventory (manual intervention needed)")

    async def _process_payment(
        self, customer_id: str, amount: Decimal, payment_method: str
    ) -> UseCaseResult[str]:
        """Process payment for the order."""
        try:
            payment_result = await self._payment.process_payment(
                customer_id, amount, payment_method
            )
            if payment_result is None:
                return self._business_error(
                    "Payment was declined", rule="PAYMENT_PROCESSING"
                )
            return Ok(payment_result.get("payment_id", str(uuid4())))
        except Exception as e:
            self._logger.exception("Payment processing failed")
            return Err(
                UseCaseError(
                    message=f"Payment service error: {e}",
                    code="PAYMENT_ERROR",
                )
            )

    async def _create_order(
        self,
        input: PlaceOrderInput,
        items: list[OrderItemOutput],
        subtotal: Decimal,
        total: Decimal,
        payment_id: str,
    ) -> UseCaseResult[PlaceOrderOutput]:
        """Create the order in the repository."""
        now = utc_now()
        order_id = str(uuid4())

        order_data = {
            "id": order_id,
            "customer_id": input.customer_id,
            "items": [
                {
                    "item_id": item.item_id,
                    "item_name": item.item_name,
                    "quantity": item.quantity,
                    "unit_price": str(item.unit_price),
                    "total_price": str(item.total_price),
                }
                for item in items
            ],
            "subtotal": str(subtotal),
            "shipping_cost": str(self.SHIPPING_COST),
            "total": str(total),
            "shipping_address": input.shipping_address,
            "payment_id": payment_id,
            "payment_method": input.payment_method,
            "status": "confirmed",
            "notes": input.notes,
            "created_at": now.isoformat(),
        }

        try:
            await self._orders.create(order_data)
        except Exception as e:
            self._logger.exception("Failed to create order")
            return Err(
                UseCaseError(
                    message=f"Failed to create order: {e}",
                    code="ORDER_CREATION_ERROR",
                )
            )

        return Ok(
            PlaceOrderOutput(
                order_id=order_id,
                customer_id=input.customer_id,
                items=items,
                subtotal=subtotal,
                shipping_cost=self.SHIPPING_COST,
                total=total,
                status="confirmed",
                estimated_delivery=now + timedelta(days=self.DELIVERY_DAYS),
                created_at=now,
            )
        )

    async def _send_notification(self, customer_id: str, order_id: str) -> None:
        """Send order confirmation notification (non-blocking)."""
        if self._notifications is None:
            return

        try:
            await self._notifications.send_order_confirmation(customer_id, order_id)
            self._logger.info("Order confirmation sent to customer %s", customer_id)
        except Exception:
            # Non-critical - log but don't fail the order
            self._logger.exception("Failed to send order confirmation")
