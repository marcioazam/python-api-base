"""Abstract mapper interface.

**Feature: application-layer-code-review-2025**
**Refactored: Split from mapper.py for one-class-per-file compliance**
"""

from abc import ABC, abstractmethod
from collections.abc import Sequence

from application.common.mappers.errors.mapper_error import MapperError


class IMapper[Source, Target](ABC):
    """Abstract base class for mappers.

    Implementations should handle field mapping, nested objects, and collections.

    Type Parameters:
        Source: Source type (entity).
        Target: Target type (DTO).
    """

    @abstractmethod
    def to_dto(self, entity: Source) -> Target:
        """Convert entity to DTO.

        Args:
            entity: Source entity to convert.

        Returns:
            Target: Converted DTO.

        Raises:
            MapperError: If mapping fails.
        """
        ...

    @abstractmethod
    def to_entity(self, dto: Target) -> Source:
        """Convert DTO to entity.

        Args:
            dto: Source DTO to convert.

        Returns:
            Source: Converted entity.

        Raises:
            MapperError: If mapping fails.
        """
        ...

    def to_dto_list(self, entities: Sequence[Source]) -> list[Target]:
        """Convert list of entities to DTOs.

        Args:
            entities: List of entities to convert.

        Returns:
            list[Target]: List of converted DTOs.
        """
        return [self.to_dto(e) for e in entities]

    def to_entity_list(self, dtos: Sequence[Target]) -> list[Source]:
        """Convert list of DTOs to entities.

        Args:
            dtos: List of DTOs to convert.

        Returns:
            list[Source]: List of converted entities.
        """
        return [self.to_entity(d) for d in dtos]


# Re-export MapperError for convenience
__all__ = ["IMapper", "MapperError"]
