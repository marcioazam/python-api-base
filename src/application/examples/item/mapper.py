"""Mapper for ItemExample.

Implements IMapper interface for entity-DTO transformations.

**Feature: application-common-integration**
**Validates: Requirements 4.1, 4.3**
"""

from collections.abc import Sequence
from decimal import Decimal

from domain.examples.item.entity import ItemExample, Money
from application.examples.shared.dtos import MoneyDTO
from application.examples.item.dtos import ItemExampleResponse
from application.common.base.mapper import IMapper


class ItemExampleMapper(IMapper[ItemExample, ItemExampleResponse]):
    """Mapper for ItemExample entity to DTOs.
    
    Implements IMapper interface for consistent mapping patterns.
    """

    def to_dto(self, entity: ItemExample) -> ItemExampleResponse:
        """Map ItemExample entity to response DTO."""
        return ItemExampleResponse(
            id=entity.id,
            name=entity.name,
            description=entity.description,
            sku=entity.sku,
            price=MoneyDTO(
                amount=entity.price.amount,
                currency=entity.price.currency,
            ),
            quantity=entity.quantity,
            status=entity.status.value,
            category=entity.category,
            tags=entity.tags,
            is_available=entity.is_available,
            total_value=MoneyDTO(
                amount=entity.total_value.amount,
                currency=entity.total_value.currency,
            ),
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            created_by=entity.created_by,
            updated_by=entity.updated_by,
        )

    def to_entity(self, dto: ItemExampleResponse) -> ItemExample:
        """Map response DTO back to ItemExample entity (for import)."""
        return ItemExample(
            id=dto.id,
            name=dto.name,
            description=dto.description,
            sku=dto.sku,
            price=Money(dto.price.amount, dto.price.currency),
            quantity=dto.quantity,
            category=dto.category,
            tags=list(dto.tags),
            created_by=dto.created_by,
        )

    def to_dto_list(self, entities: Sequence[ItemExample]) -> list[ItemExampleResponse]:
        """Map list of entities to response DTOs."""
        return [self.to_dto(e) for e in entities]

    def to_entity_list(self, dtos: Sequence[ItemExampleResponse]) -> list[ItemExample]:
        """Map list of DTOs to entities."""
        return [self.to_entity(d) for d in dtos]

    # Backward compatibility static methods
    @staticmethod
    def to_response(entity: ItemExample) -> ItemExampleResponse:
        """Static method for backward compatibility."""
        return ItemExampleMapper().to_dto(entity)

    @staticmethod
    def to_response_list(entities: list[ItemExample]) -> list[ItemExampleResponse]:
        """Static method for backward compatibility."""
        return ItemExampleMapper().to_dto_list(entities)
