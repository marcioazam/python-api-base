"""Auto mapper that infers mapping from type hints.

**Feature: application-layer-code-review-2025**
**Refactored: Split from mapper.py for one-class-per-file compliance**
"""

from pydantic import BaseModel

from application.common.mappers.interfaces.mapper_interface import IMapper


class AutoMapper[Source: BaseModel, Target: BaseModel](IMapper[Source, Target]):
    """Auto mapper that infers mapping from type hints.

    Automatically maps between types based on field names without
    requiring explicit configuration.

    Type Parameters:
        Source: Source Pydantic model type.
        Target: Target Pydantic model type.
    """

    def __init__(self, source_type: type[Source], target_type: type[Target]) -> None:
        """Initialize auto mapper.

        Args:
            source_type: Source model type.
            target_type: Target model type.
        """
        self._source_type = source_type
        self._target_type = target_type

    def to_dto(self, entity: Source) -> Target:
        """Convert entity to DTO.

        Args:
            entity: Source entity.

        Returns:
            Target: Converted DTO.
        """
        data = entity.model_dump()
        target_fields = set(self._target_type.model_fields.keys())
        filtered_data = {k: v for k, v in data.items() if k in target_fields}
        return self._target_type.model_validate(filtered_data)

    def to_entity(self, dto: Target) -> Source:
        """Convert DTO to entity.

        Args:
            dto: Source DTO.

        Returns:
            Source: Converted entity.
        """
        data = dto.model_dump()
        source_fields = set(self._source_type.model_fields.keys())
        filtered_data = {k: v for k, v in data.items() if k in source_fields}
        return self._source_type.model_validate(filtered_data)
