"""Use cases for ItemExample and PedidoExample.

Demonstrates:
- BaseUseCase pattern
- Result pattern for error handling
- Repository integration
- Event publishing
- Cache integration
- Audit logging

**Feature: example-system-demo**
"""

from decimal import Decimal
from typing import Any
import logging

from core.base.result import Result, Ok, Err
from domain.examples.item_example import ItemExample, Money
from domain.examples.pedido_example import PedidoExample
from application.examples.dtos import (
    ItemExampleCreate,
    ItemExampleUpdate,
    ItemExampleResponse,
    PedidoExampleCreate,
    PedidoExampleUpdate,
    PedidoExampleResponse,
    AddItemRequest,
)
from application.examples.mappers import ItemExampleMapper, PedidoExampleMapper

logger = logging.getLogger(__name__)


class UseCaseError(Exception):
    """Base error for use case failures."""

    def __init__(self, message: str, code: str = "USE_CASE_ERROR") -> None:
        self.message = message
        self.code = code
        super().__init__(message)


class NotFoundError(UseCaseError):
    """Entity not found error."""

    def __init__(self, entity: str, entity_id: str) -> None:
        super().__init__(f"{entity} with id '{entity_id}' not found", "NOT_FOUND")
        self.entity = entity
        self.entity_id = entity_id


class ValidationError(UseCaseError):
    """Validation error."""

    def __init__(self, message: str, field: str | None = None) -> None:
        super().__init__(message, "VALIDATION_ERROR")
        self.field = field


class ItemExampleUseCase:
    """Use case for ItemExample CRUD operations.

    Demonstrates:
    - Repository pattern usage
    - Result pattern for errors
    - Event publishing after mutations
    - Cache invalidation
    - Structured logging

    Example:
        >>> use_case = ItemExampleUseCase(repository, event_bus, cache)
        >>> result = await use_case.create(ItemExampleCreate(...))
        >>> if result.is_ok():
        ...     item = result.unwrap()
    """

    def __init__(
        self,
        repository: Any,  # ItemExampleRepository
        event_bus: Any | None = None,
        cache: Any | None = None,
    ) -> None:
        self._repo = repository
        self._event_bus = event_bus
        self._cache = cache

    async def create(
        self,
        data: ItemExampleCreate,
        created_by: str = "system",
    ) -> Result[ItemExampleResponse, UseCaseError]:
        """Create a new ItemExample."""
        try:
            # Check for duplicate SKU
            existing = await self._repo.get_by_sku(data.sku)
            if existing:
                return Err(ValidationError(f"SKU '{data.sku}' already exists", "sku"))

            # Create entity
            item = ItemExample.create(
                name=data.name,
                description=data.description,
                sku=data.sku,
                price=Money(data.price.amount, data.price.currency),
                quantity=data.quantity,
                category=data.category,
                tags=data.tags,
                created_by=created_by,
            )
            item.metadata = data.metadata

            # Persist
            saved = await self._repo.create(item)

            # Publish events
            if self._event_bus:
                for event in saved.events:
                    await self._event_bus.publish(event)
                saved.clear_events()

            # Invalidate cache
            if self._cache:
                await self._cache.delete("items:list")

            logger.info(
                f"ItemExample created: {saved.id}",
                extra={"item_id": saved.id, "sku": saved.sku},
            )

            return Ok(ItemExampleMapper.to_response(saved))

        except Exception as e:
            logger.error(f"Failed to create ItemExample: {e}", exc_info=True)
            return Err(UseCaseError(str(e)))

    async def get(self, item_id: str) -> Result[ItemExampleResponse, UseCaseError]:
        """Get ItemExample by ID."""
        # Try cache first
        if self._cache:
            cached = await self._cache.get(f"item:{item_id}")
            if cached:
                return Ok(cached)

        item = await self._repo.get(item_id)
        if not item:
            return Err(NotFoundError("ItemExample", item_id))

        response = ItemExampleMapper.to_response(item)

        # Cache result
        if self._cache:
            await self._cache.set(f"item:{item_id}", response, ttl=300)

        return Ok(response)

    async def update(
        self,
        item_id: str,
        data: ItemExampleUpdate,
        updated_by: str = "system",
    ) -> Result[ItemExampleResponse, UseCaseError]:
        """Update an ItemExample."""
        item = await self._repo.get(item_id)
        if not item:
            return Err(NotFoundError("ItemExample", item_id))

        # Apply updates
        price = None
        if data.price:
            price = Money(data.price.amount, data.price.currency)

        item.update(
            name=data.name,
            description=data.description,
            price=price,
            quantity=data.quantity,
            category=data.category,
            updated_by=updated_by,
        )

        if data.tags is not None:
            item.tags = data.tags

        if data.status is not None:
            item.status = data.status

        # Persist
        saved = await self._repo.update(item)

        # Publish events
        if self._event_bus:
            for event in saved.events:
                await self._event_bus.publish(event)
            saved.clear_events()

        # Invalidate cache
        if self._cache:
            await self._cache.delete(f"item:{item_id}")
            await self._cache.delete("items:list")

        logger.info(f"ItemExample updated: {item_id}")

        return Ok(ItemExampleMapper.to_response(saved))

    async def delete(
        self,
        item_id: str,
        deleted_by: str = "system",
    ) -> Result[bool, UseCaseError]:
        """Soft delete an ItemExample."""
        item = await self._repo.get(item_id)
        if not item:
            return Err(NotFoundError("ItemExample", item_id))

        item.soft_delete(deleted_by)
        await self._repo.update(item)

        # Publish events
        if self._event_bus:
            for event in item.events:
                await self._event_bus.publish(event)
            item.clear_events()

        # Invalidate cache
        if self._cache:
            await self._cache.delete(f"item:{item_id}")
            await self._cache.delete("items:list")

        logger.info(f"ItemExample deleted: {item_id}")

        return Ok(True)

    async def list(
        self,
        page: int = 1,
        page_size: int = 20,
        category: str | None = None,
        status: str | None = None,
    ) -> Result[list[ItemExampleResponse], UseCaseError]:
        """List ItemExamples with filtering."""
        items = await self._repo.get_all(
            page=page,
            page_size=page_size,
            category=category,
            status=status,
        )
        return Ok(ItemExampleMapper.to_response_list(items))


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
                    return Err(
                        ValidationError(f"Item '{item.name}' is not available")
                    )
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
