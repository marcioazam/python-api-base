"""Item mapper implementation with structured logging.

**Feature: application-layer-code-review-v2, Tasks 1.1-1.3**
**Validates: Requirements 1.1, 1.2, 1.3, 2.1, 2.2, 2.3, 5.2**
"""

import logging
from datetime import datetime, UTC
from typing import Final

from pydantic import ValidationError

from my_api.domain.entities.item import Item, ItemResponse
from my_api.shared.mapper import IMapper, MapperError

logger: Final[logging.Logger] = logging.getLogger(__name__)


class ItemMapper(IMapper[Item, ItemResponse]):
    """Mapper for Item entity to ItemResponse DTO.

    Thread-safe, stateless mapper with structured logging
    and comprehensive error handling.
    """

    def to_dto(self, entity: Item) -> ItemResponse:
        """Convert Item entity to ItemResponse DTO.

        Args:
            entity: Item entity to convert.

        Returns:
            ItemResponse DTO with all entity fields mapped.

        Raises:
            TypeError: If entity is not an Item instance.
            ValueError: If entity is None.
            MapperError: If conversion fails due to validation.
        """
        if entity is None:
            raise ValueError("entity parameter cannot be None")
        if not isinstance(entity, Item):
            raise TypeError(
                f"Expected Item instance, got {type(entity).__name__}"
            )

        log_context = {
            "entity_type": "Item",
            "operation": "to_dto",
            "entity_id": getattr(entity, "id", None),
            "timestamp": datetime.now(UTC).isoformat(),
        }

        try:
            logger.debug(
                "Mapping entity to DTO",
                extra={"context": log_context},
            )
            result = ItemResponse.model_validate(entity)
            logger.debug(
                "Mapping completed successfully",
                extra={"context": {**log_context, "success": True}},
            )
            return result

        except ValidationError as e:
            logger.error(
                "Validation failed during mapping",
                extra={
                    "context": {
                        **log_context,
                        "error_type": "ValidationError",
                        "error_count": len(e.errors()),
                    }
                },
                exc_info=True,
            )
            raise MapperError(
                message=f"Failed to convert Item to ItemResponse: {e}",
                context={"entity_id": log_context["entity_id"]},
            ) from e

    def to_entity(self, dto: ItemResponse) -> Item:
        """Convert ItemResponse DTO to Item entity.

        Args:
            dto: ItemResponse DTO to convert.

        Returns:
            Item entity with all DTO fields mapped.

        Raises:
            TypeError: If dto is not an ItemResponse instance.
            ValueError: If dto is None.
            MapperError: If conversion fails due to validation.
        """
        if dto is None:
            raise ValueError("dto parameter cannot be None")
        if not isinstance(dto, ItemResponse):
            raise TypeError(
                f"Expected ItemResponse instance, got {type(dto).__name__}"
            )

        log_context = {
            "entity_type": "ItemResponse",
            "operation": "to_entity",
            "dto_id": getattr(dto, "id", None),
            "timestamp": datetime.now(UTC).isoformat(),
        }

        try:
            logger.debug(
                "Mapping DTO to entity",
                extra={"context": log_context},
            )
            # Exclude computed fields from conversion
            data = dto.model_dump(exclude={"price_with_tax"})
            result = Item.model_validate(data)
            logger.debug(
                "Mapping completed successfully",
                extra={"context": {**log_context, "success": True}},
            )
            return result

        except ValidationError as e:
            logger.error(
                "Validation failed during mapping",
                extra={
                    "context": {
                        **log_context,
                        "error_type": "ValidationError",
                        "error_count": len(e.errors()),
                    }
                },
                exc_info=True,
            )
            raise MapperError(
                message=f"Failed to convert ItemResponse to Item: {e}",
                context={"dto_id": log_context["dto_id"]},
            ) from e
