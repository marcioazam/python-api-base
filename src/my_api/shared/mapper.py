"""Generic mapper interface and base implementation for object conversion.

Uses PEP 695 type parameter syntax (Python 3.12+) for cleaner generic definitions.
"""

from abc import ABC, abstractmethod
from typing import Any
from collections.abc import Sequence

from pydantic import BaseModel


class MapperError(Exception):
    """Raised when mapping fails."""

    def __init__(self, message: str, field: str | None = None, context: dict | None = None) -> None:
        """Initialize mapper error.

        Args:
            message: Error message.
            field: Field that caused the error.
            context: Additional context about the error.
        """
        self.field = field
        self.context = context or {}
        super().__init__(message)


class IMapper[Source: BaseModel, Target: BaseModel](ABC):
    """Generic mapper interface for object conversion.

    Defines the contract for converting between entity and DTO types.
    Implementations should handle field mapping, nested objects, and collections.
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


class BaseMapper[Source: BaseModel, Target: BaseModel](IMapper[Source, Target]):
    """Base mapper with automatic field mapping.

    Provides default implementation that maps fields with matching names
    between source and target types. Supports nested objects and collections.
    """

    def __init__(
        self,
        source_type: type[Source],
        target_type: type[Target],
        field_mapping: dict[str, str] | None = None,
        exclude_fields: set[str] | None = None,
    ) -> None:
        """Initialize base mapper.

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
        # Reverse the field mapping for DTO to entity conversion
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

        # Get target field names
        target_fields = set(target_type.model_fields.keys())

        for source_field, value in source_data.items():
            if source_field in self._exclude_fields:
                continue

            # Apply field mapping if defined
            target_field = field_mapping.get(source_field, source_field)

            # Only include if target has this field
            if target_field in target_fields:
                target_data[target_field] = self._map_value(value)

        # Check for missing required fields
        for field_name, field_info in target_type.model_fields.items():
            if field_name not in target_data and field_info.is_required():
                raise MapperError(
                    message=f"Required field '{field_name}' is missing in source",
                    field=field_name,
                    context={"source_type": type(source).__name__, "target_type": target_type.__name__},
                )

        try:
            return target_type.model_validate(target_data)
        except Exception as e:
            raise MapperError(
                message=f"Failed to create {target_type.__name__}: {e}",
                context={"source_type": type(source).__name__, "target_type": target_type.__name__},
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
            # Recursively map nested Pydantic models
            return value.model_dump()

        if isinstance(value, list):
            return [self._map_value(item) for item in value]

        if isinstance(value, dict):
            return {k: self._map_value(v) for k, v in value.items()}

        return value


class AutoMapper[Source: BaseModel, Target: BaseModel](IMapper[Source, Target]):
    """Auto mapper that infers mapping from type hints.

    Automatically maps between types based on field names without
    requiring explicit configuration.
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
