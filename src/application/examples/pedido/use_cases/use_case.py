"""Use case for PedidoExample operations.

Demonstrates:
- Complex aggregate operations
- Cross-entity validation
- Transaction boundaries
- Multi-tenant awareness

**Feature: example-system-demo**
"""

import logging
from typing import Any

from application.examples.pedido.dtos import (
    AddItemRequest,
    PedidoExampleCreate,
    PedidoExampleResponse,
)
from application.examples.pedido.mapper import PedidoExampleMapper
from application.examples.shared.errors import (
    NotFoundError,
    UseCaseError,
    ValidationError,
)
from core.base.patterns.result import Err, Ok, Result
from domain.examples.pedido.entity import PedidoExample

logger = logging.getLogger(__name__)


class PedidoExampleUseCase:
    """Use case for PedidoExample operations.

    Demonstrates:
    - Complex aggregate operations
    - Cross-entity validation
    - Transaction boundaries
    - Multi-tenant awareness
    """

    def __init__(
        self,
        pedido_repo: Any,  # PedidoExampleRepository
        item_repo: Any,  # ItemExampleRepository
        event_bus: Any | None = None,
        cache: Any | None = None,
    ) -> None:
        self._pedido_repo = pedido_repo
        self._item_repo = item_repo
        self._event_bus = event_bus
        self._cache = cache

    async def create(
        self,
        data: PedidoExampleCreate,
        tenant_id: str | None = None,
        created_by: str = "system",
    ) -> Result[PedidoExampleResponse, UseCaseError]:
        """Create a new order with optional items."""
        try:
            # Create order
            pedido = PedidoExample.create(
                customer_id=data.customer_id,
                customer_name=data.customer_name,
                customer_email=data.customer_email,
                shipping_address=data.shipping_address,
                notes=data.notes,
                tenant_id=tenant_id,
                created_by=created_by,
            )

            # Add items if provided
            for item_req in data.items:
                item = await self._item_repo.get(item_req.item_id)
                if not item:
                    return Err(NotFoundError("ItemExample", item_req.item_id))
                if not item.is_available:
                    return Err(ValidationError(f"Item '{item.name}' is not available"))
                if item.quantity < item_req.quantity:
                    return Err(
                        ValidationError(
                            f"Insufficient stock for '{item.name}'. "
                            f"Available: {item.quantity}, Requested: {item_req.quantity}"
                        )
                    )

                pedido.add_item(
                    item_id=item.id,
                    item_name=item.name,
                    quantity=item_req.quantity,
                    unit_price=item.price,
                    discount=item_req.discount,
                )

            # Persist
            saved = await self._pedido_repo.create(pedido)

            # Publish events
            if self._event_bus:
                for event in saved.events:
                    await self._event_bus.publish(event)
                saved.clear_events()

            logger.info(
                f"PedidoExample created: {saved.id}",
                extra={
                    "pedido_id": saved.id,
                    "customer_id": saved.customer_id,
                    "items_count": saved.items_count,
                },
            )

            return Ok(PedidoExampleMapper.to_response(saved))

        except Exception as e:
            logger.error(f"Failed to create PedidoExample: {e}", exc_info=True)
            return Err(UseCaseError(str(e)))

    async def get(self, pedido_id: str) -> Result[PedidoExampleResponse, UseCaseError]:
        """Get order by ID."""
        pedido = await self._pedido_repo.get(pedido_id)
        if not pedido:
            return Err(NotFoundError("PedidoExample", pedido_id))
        return Ok(PedidoExampleMapper.to_response(pedido))

    async def add_item(
        self,
        pedido_id: str,
        data: AddItemRequest,
    ) -> Result[PedidoExampleResponse, UseCaseError]:
        """Add an item to an order."""
        pedido = await self._pedido_repo.get(pedido_id)
        if not pedido:
            return Err(NotFoundError("PedidoExample", pedido_id))

        if not pedido.can_be_modified:
            return Err(
                ValidationError(
                    f"Order in '{pedido.status.value}' status cannot be modified"
                )
            )

        item = await self._item_repo.get(data.item_id)
        if not item:
            return Err(NotFoundError("ItemExample", data.item_id))

        if not item.is_available:
            return Err(ValidationError(f"Item '{item.name}' is not available"))

        try:
            pedido.add_item(
                item_id=item.id,
                item_name=item.name,
                quantity=data.quantity,
                unit_price=item.price,
                discount=data.discount,
            )
            saved = await self._pedido_repo.update(pedido)

            if self._event_bus:
                for event in saved.events:
                    await self._event_bus.publish(event)
                saved.clear_events()

            return Ok(PedidoExampleMapper.to_response(saved))

        except ValueError as e:
            return Err(ValidationError(str(e)))

    async def confirm(
        self,
        pedido_id: str,
        confirmed_by: str = "system",
    ) -> Result[PedidoExampleResponse, UseCaseError]:
        """Confirm an order."""
        pedido = await self._pedido_repo.get(pedido_id)
        if not pedido:
            return Err(NotFoundError("PedidoExample", pedido_id))

        try:
            pedido.confirm(confirmed_by)
            saved = await self._pedido_repo.update(pedido)

            if self._event_bus:
                for event in saved.events:
                    await self._event_bus.publish(event)
                saved.clear_events()

            logger.info(
                f"PedidoExample confirmed: {pedido_id}",
                extra={"pedido_id": pedido_id, "total": str(pedido.total.amount)},
            )

            return Ok(PedidoExampleMapper.to_response(saved))

        except ValueError as e:
            return Err(ValidationError(str(e)))

    async def cancel(
        self,
        pedido_id: str,
        reason: str,
        cancelled_by: str = "system",
    ) -> Result[PedidoExampleResponse, UseCaseError]:
        """Cancel an order."""
        pedido = await self._pedido_repo.get(pedido_id)
        if not pedido:
            return Err(NotFoundError("PedidoExample", pedido_id))

        if not pedido.can_be_cancelled:
            return Err(
                ValidationError(
                    f"Order in '{pedido.status.value}' status cannot be cancelled"
                )
            )

        try:
            pedido.cancel(reason, cancelled_by)
            saved = await self._pedido_repo.update(pedido)

            if self._event_bus:
                for event in saved.events:
                    await self._event_bus.publish(event)
                saved.clear_events()

            logger.info(
                f"PedidoExample cancelled: {pedido_id}",
                extra={"pedido_id": pedido_id, "reason": reason},
            )

            return Ok(PedidoExampleMapper.to_response(saved))

        except ValueError as e:
            return Err(ValidationError(str(e)))

    async def list(
        self,
        page: int = 1,
        page_size: int = 20,
        customer_id: str | None = None,
        status: str | None = None,
        tenant_id: str | None = None,
    ) -> Result[list[PedidoExampleResponse], UseCaseError]:
        """List orders with filtering."""
        pedidos = await self._pedido_repo.get_all(
            page=page,
            page_size=page_size,
            customer_id=customer_id,
            status=status,
            tenant_id=tenant_id,
        )
        return Ok(PedidoExampleMapper.to_response_list(pedidos))
