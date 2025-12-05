"""Generic mapper with automatic field mapping.

**Feature: application-layer-code-review-2025**
**Refactored: Split from mapper.py for one-class-per-file compliance**
"""

from typing import Any

from pydantic import BaseModel

from application.common.mappers.errors.mapper_error import MapperError
from application.common.mappers.interfaces.mapper_interface import IMapper


class GenericMapper[Source: BaseModel, Target: BaseModel](IMapper[Source, Target]):
    """Generic mapper with automatic field mapping.

    Provides default implementation that maps fields with matching names
    between source and target types. Supports nested objects and collections.

    Type Parameters:
        Source: Source Pydantic model type.
        Target: Target Pydantic model type.

    Example:
        >>> mapper = GenericMapper(UserEntity, UserDTO)
        >>> dto = mapper.to_dto(user_entity)
        >>> entity = mapper.to_entity(user_dto)
    """

    def __init__(
        self,
        source_type: type[Source],
        target_type: type[Target],
        field_mapping: dict[str, str] | None = None,
        exclude_fields: set[str] | None = None,
    ) -> None:
        """Initialize generic mapper.

        Args:
            source_type: Source model type.
            target_type: Target model type.
            field_mapping: Optional mapping of source field names to target field names.
            exclude_fields: Fields to exclude from mapping.
        """
        self._source_type = source_type
        self._target_type = target_type
        self._field_mapping = field_mapping or {}
        self._exclude_fields = exclude_fields or set()

    def to_dto(self, entity: Source) -> Target:
        """Convert entity to DTO using automatic field mapping.

        Args:
            entity: Source entity to convert.

        Returns:
            Target: Converted DTO.

        Raises:
            MapperError: If required fields are missing.
        """
        return self._map(entity, self._target_type, self._field_mapping)

    def to_entity(self, dto: Target) -> Source:
        """Convert DTO to entity using automatic field mapping.

        Args:
            dto: Source DTO to convert.

        Returns:
            Source: Converted entity.

        Raises:
            MapperError: If required fields are missing.
        """
        reverse_mapping = {v: k for k, v in self._field_mapping.items()}
        return self._map(dto, self._source_type, reverse_mapping)

    def _map(
        self,
        source: BaseModel,
        target_type: type[BaseModel],
        field_mapping: dict[str, str],
    ) -> Any:
        """Map source object to target type.

        Args:
            source: Source object.
            target_type: Target type to create.
            field_mapping: Field name mapping.

        Returns:
            Instance of target type.

        Raises:
            MapperError: If mapping fails.
        """
        source_data = source.model_dump()
        target_data: dict[str, Any] = {}

        target_fields = set(target_type.model_fields.keys())

        for source_field, value in source_data.items():
            if source_field in self._exclude_fields:
                continue

            target_field = field_mapping.get(source_field, source_field)

            if target_field in target_fields:
                target_data[target_field] = self._map_value(value)

        for field_name, field_info in target_type.model_fields.items():
            if field_name not in target_data and field_info.is_required():
                raise MapperError(
                    message=f"Required field '{field_name}' is missing in source",
                    field=field_name,
                    context={
                        "source_type": type(source).__name__,
                        "target_type": target_type.__name__,
                    },
                )

        try:
            return target_type.model_validate(target_data)
        except Exception as e:
            raise MapperError(
                message=f"Failed to create {target_type.__name__}: {e}",
                context={
                    "source_type": type(source).__name__,
                    "target_type": target_type.__name__,
                },
            ) from e

    def _map_value(self, value: Any) -> Any:
        """Map a single value, handling nested objects and collections.

        Args:
            value: Value to map.

        Returns:
            Mapped value.
        """
        if value is None:
            return None

        if isinstance(value, BaseModel):
            return value.model_dump()

        if isinstance(value, list):
            return [self._map_value(item) for item in value]

        if isinstance(value, dict):
            return {k: self._map_value(v) for k, v in value.items()}

        return value
