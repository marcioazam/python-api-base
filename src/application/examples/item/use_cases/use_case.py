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
**Feature: application-layer-code-review-2025**
**Validates: Requirements 3.1, 3.2, 3.3, 3.5**
**Refactored: Extracted reusable services**
"""

import logging
from typing import Any

from application.common.mixins.event_publishing import EventPublishingMixin
from application.common.services.cache_service import CacheService
from application.common.services.kafka_event_service import KafkaEventService
from application.examples.item.dtos import (
    ItemExampleCreate,
    ItemExampleResponse,
    ItemExampleUpdate,
)
from application.examples.item.mapper import ItemExampleMapper
from application.examples.shared.errors import (
    NotFoundError,
    UseCaseError,
    ValidationError,
)
from core.base.patterns.result import Err, Ok, Result
from domain.examples.item.entity import ItemExample, Money

logger = logging.getLogger(__name__)


class ItemExampleUseCase(EventPublishingMixin):
    """Use case for ItemExample CRUD operations.

    Uses extracted services for event publishing and caching.

    Example:
        >>> use_case = ItemExampleUseCase(repository, event_bus, cache)
        >>> result = await use_case.create(ItemExampleCreate(...))
        >>> if result.is_ok():
        ...     item = result.unwrap()
    """

    def __init__(
        self,
        repository: Any,
        event_bus: Any | None = None,
        cache: Any | None = None,
        kafka_publisher: Any | None = None,
    ) -> None:
        """Initialize use case with repository and optional services."""
        self._repo = repository
        self._event_bus = event_bus
        self._cache_service = CacheService(cache, prefix="item")
        self._kafka_service = KafkaEventService(kafka_publisher)

    async def create(
        self,
        data: ItemExampleCreate,
        created_by: str = "system",
    ) -> Result[ItemExampleResponse, UseCaseError]:
        """Create a new ItemExample."""
        try:
            existing = await self._repo.get_by_sku(data.sku)
            if existing:
                return Err(ValidationError(f"SKU '{data.sku}' already exists", "sku"))

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
            saved = await self._repo.create(item)

            await self._publish_events(saved)
            await self._publish_item_created_event(saved, created_by)
            await self._cache_service.invalidate("list")

            logger.info(f"ItemExample created: {saved.id}", extra={"item_id": saved.id})
            return Ok(ItemExampleMapper.to_response(saved))

        except Exception as e:
            logger.error(f"Failed to create ItemExample: {e}", exc_info=True)
            return Err(UseCaseError(str(e)))

    async def _publish_item_created_event(
        self, item: ItemExample, created_by: str
    ) -> None:
        """Publish ItemCreated event to Kafka."""
        from infrastructure.kafka.event_publisher import ItemCreatedEvent

        await self._kafka_service.publish_event(
            event_type="ItemCreated",
            entity_type="ItemExample",
            entity_id=item.id,
            payload=ItemCreatedEvent(
                id=item.id, name=item.name, sku=item.sku,
                quantity=item.quantity, created_by=created_by
            ),
            topic="items-events",
        )

    async def get(self, item_id: str) -> Result[ItemExampleResponse, UseCaseError]:
        """Get ItemExample by ID."""
        cached = await self._cache_service.get(item_id)
        if cached:
            return Ok(cached)

        item = await self._repo.get(item_id)
        if not item:
            return Err(NotFoundError("ItemExample", item_id))

        response = ItemExampleMapper.to_response(item)
        await self._cache_service.set(item_id, response)
        return Ok(response)

    def _apply_update_fields(
        self,
        item: ItemExample,
        data: ItemExampleUpdate,
        updated_by: str,
    ) -> None:
        """Apply update fields to item entity."""
        if data.name is not None:
            item.name = data.name
        if data.description is not None:
            item.description = data.description
        if data.price is not None:
            item.update_price(Money(data.price.amount, data.price.currency), updated_by)
        if data.quantity is not None:
            item.update_quantity(data.quantity, updated_by)
        if data.category is not None:
            item.category = data.category
        if data.tags is not None:
            item.tags = data.tags
        if data.metadata is not None:
            item.metadata = data.metadata

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
            self._apply_update_fields(item, data, updated_by)
            saved = await self._repo.update(item)

            await self._publish_events(saved)
            await self._publish_item_updated_event(saved, data, updated_by)
            await self._cache_service.invalidate(item_id)

            logger.info(f"ItemExample updated: {saved.id}", extra={"item_id": saved.id})
            return Ok(ItemExampleMapper.to_response(saved))

        except ValueError as e:
            return Err(ValidationError(str(e)))

    async def _publish_item_updated_event(
        self, item: ItemExample, data: ItemExampleUpdate, updated_by: str
    ) -> None:
        """Publish ItemUpdated event to Kafka."""
        from infrastructure.kafka.event_publisher import ItemUpdatedEvent

        await self._kafka_service.publish_event(
            event_type="ItemUpdated",
            entity_type="ItemExample",
            entity_id=item.id,
            payload=ItemUpdatedEvent(
                id=item.id,
                changes=data.model_dump(exclude_unset=True),
                updated_by=updated_by,
            ),
            topic="items-events",
        )

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

        await self._publish_events(item)
        await self._publish_item_deleted_event(item_id, deleted_by)
        await self._cache_service.invalidate(item_id)

        logger.info(f"ItemExample deleted: {item_id}", extra={"item_id": item_id})
        return Ok(True)

    async def _publish_item_deleted_event(self, item_id: str, deleted_by: str) -> None:
        """Publish ItemDeleted event to Kafka."""
        from infrastructure.kafka.event_publisher import ItemDeletedEvent

        await self._kafka_service.publish_event(
            event_type="ItemDeleted",
            entity_type="ItemExample",
            entity_id=item_id,
            payload=ItemDeletedEvent(id=item_id, deleted_by=deleted_by),
            topic="items-events",
        )

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
