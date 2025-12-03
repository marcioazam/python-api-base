"""Use case for ItemExample operations.

Demonstrates:
- Repository pattern usage
- Result pattern for errors
- Event publishing after mutations
- Kafka event publishing for domain events
- Cache invalidation
- Structured logging

**Feature: example-system-demo**
**Feature: kafka-workflow-integration**
**Validates: Requirements 3.1, 3.2, 3.3, 3.5**
"""

import logging
from typing import Any, TYPE_CHECKING

from core.base.patterns.result import Result, Ok, Err
from domain.examples.item.entity import ItemExample, Money
from application.examples.item.dtos import (
    ItemExampleCreate,
    ItemExampleUpdate,
    ItemExampleResponse,
)
from application.examples.item.mapper import ItemExampleMapper
from application.examples.shared.errors import UseCaseError, NotFoundError, ValidationError

if TYPE_CHECKING:
    from infrastructure.kafka.event_publisher import EventPublisher

logger = logging.getLogger(__name__)


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
        kafka_publisher: "EventPublisher | None" = None,
    ) -> None:
        """Initialize use case.

        Args:
            repository: ItemExampleRepository instance
            event_bus: Optional in-memory event bus
            cache: Optional cache client
            kafka_publisher: Optional Kafka event publisher for domain events
        """
        self._repo = repository
        self._event_bus = event_bus
        self._cache = cache
        self._kafka_publisher = kafka_publisher

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

            # Publish Kafka event
            # **Feature: kafka-workflow-integration**
            # **Validates: Requirements 3.1, 3.5**
            if self._kafka_publisher:
                try:
                    from infrastructure.kafka.event_publisher import (
                        DomainEvent,
                        ItemCreatedEvent,
                    )

                    kafka_event = DomainEvent(
                        event_type="ItemCreated",
                        entity_type="ItemExample",
                        entity_id=saved.id,
                        payload=ItemCreatedEvent(
                            id=saved.id,
                            name=saved.name,
                            sku=saved.sku,
                            quantity=saved.quantity,
                            created_by=created_by,
                        ),
                    )
                    await self._kafka_publisher.publish(kafka_event, "items-events")
                except Exception as e:
                    logger.error(f"Failed to publish Kafka event: {e}")

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

        try:
            # Update fields
            if data.name is not None:
                item.name = data.name
            if data.description is not None:
                item.description = data.description
            if data.price is not None:
                item.update_price(
                    Money(data.price.amount, data.price.currency),
                    updated_by,
                )
            if data.quantity is not None:
                item.update_quantity(data.quantity, updated_by)
            if data.category is not None:
                item.category = data.category
            if data.tags is not None:
                item.tags = data.tags
            if data.metadata is not None:
                item.metadata = data.metadata

            saved = await self._repo.update(item)

            # Publish events
            if self._event_bus:
                for event in saved.events:
                    await self._event_bus.publish(event)
                saved.clear_events()

            # Publish Kafka event
            # **Feature: kafka-workflow-integration**
            # **Validates: Requirements 3.2, 3.5**
            if self._kafka_publisher:
                try:
                    from infrastructure.kafka.event_publisher import (
                        DomainEvent,
                        ItemUpdatedEvent,
                    )

                    changes = data.model_dump(exclude_unset=True)
                    kafka_event = DomainEvent(
                        event_type="ItemUpdated",
                        entity_type="ItemExample",
                        entity_id=saved.id,
                        payload=ItemUpdatedEvent(
                            id=saved.id,
                            changes=changes,
                            updated_by=updated_by,
                        ),
                    )
                    await self._kafka_publisher.publish(kafka_event, "items-events")
                except Exception as e:
                    logger.error(f"Failed to publish Kafka event: {e}")

            # Invalidate cache
            if self._cache:
                await self._cache.delete(f"item:{item_id}")
                await self._cache.delete("items:list")

            logger.info(
                f"ItemExample updated: {saved.id}",
                extra={"item_id": saved.id},
            )

            return Ok(ItemExampleMapper.to_response(saved))

        except ValueError as e:
            return Err(ValidationError(str(e)))

    async def delete(
        self,
        item_id: str,
        deleted_by: str = "system",
    ) -> Result[bool, UseCaseError]:
        """Soft delete an ItemExample."""
        item = await self._repo.get(item_id)
        if not item:
            return Err(NotFoundError("ItemExample", item_id))

        item.delete(deleted_by)
        await self._repo.update(item)

        # Publish events
        if self._event_bus:
            for event in item.events:
                await self._event_bus.publish(event)
            item.clear_events()

        # Publish Kafka event
        # **Feature: kafka-workflow-integration**
        # **Validates: Requirements 3.3, 3.5**
        if self._kafka_publisher:
            try:
                from infrastructure.kafka.event_publisher import (
                    DomainEvent,
                    ItemDeletedEvent,
                )

                kafka_event = DomainEvent(
                    event_type="ItemDeleted",
                    entity_type="ItemExample",
                    entity_id=item_id,
                    payload=ItemDeletedEvent(
                        id=item_id,
                        deleted_by=deleted_by,
                    ),
                )
                await self._kafka_publisher.publish(kafka_event, "items-events")
            except Exception as e:
                logger.error(f"Failed to publish Kafka event: {e}")

        # Invalidate cache
        if self._cache:
            await self._cache.delete(f"item:{item_id}")
            await self._cache.delete("items:list")

        logger.info(
            f"ItemExample deleted: {item_id}",
            extra={"item_id": item_id, "deleted_by": deleted_by},
        )

        return Ok(True)

    async def list(
        self,
        page: int = 1,
        page_size: int = 20,
        category: str | None = None,
        status: str | None = None,
    ) -> Result[list[ItemExampleResponse], UseCaseError]:
        """List items with filtering."""
        items = await self._repo.get_all(
            page=page,
            page_size=page_size,
            category=category,
            status=status,
        )
        return Ok(ItemExampleMapper.to_response_list(items))
