"""Mapper protocol definition.

**Feature: application-layer-code-review-2025**
**Refactored: Split from mapper.py for one-class-per-file compliance**
"""

from collections.abc import Sequence
from typing import Protocol


class Mapper[TSource, TTarget](Protocol):
    """Protocol for mappers.

    Type Parameters:
        TSource: Source type.
        TTarget: Target type.
    """

    def to_dto(self, entity: TSource) -> TTarget:
        """Convert entity to DTO."""
        ...

    def to_entity(self, dto: TTarget) -> TSource:
        """Convert DTO to entity."""
        ...

    def to_dto_list(self, entities: Sequence[TSource]) -> list[TTarget]:
        """Convert list of entities to DTOs."""
        ...

    def to_entity_list(self, dtos: Sequence[TTarget]) -> list[TSource]:
        """Convert list of DTOs to entities."""
        ...
