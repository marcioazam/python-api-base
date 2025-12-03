"""GraphQL type mapping from Pydantic models.

**Feature: python-api-base-2025-generics-audit**
**Validates: Requirements 20.1**
"""

from collections.abc import Callable
from typing import Protocol, runtime_checkable

from pydantic import BaseModel


@runtime_checkable
class GraphQLType[T: BaseModel](Protocol):
    """Protocol for GraphQL type mapping from Pydantic models.

    Type Parameters:
        T: The Pydantic model type.

    **Feature: python-api-base-2025-generics-audit**
    **Validates: Requirements 20.1**
    """

    @classmethod
    def from_pydantic(cls, model: type[T]) -> "GraphQLType[T]":
        """Create GraphQL type from Pydantic model."""
        ...

    def to_graphql_schema(self) -> str:
        """Generate GraphQL schema definition."""
        ...

    def get_field_resolvers(self) -> dict[str, Callable]:
        """Get field resolvers for this type."""
        ...


class PydanticGraphQLMapper[T: BaseModel]:
    """Maps Pydantic models to GraphQL types.

    Type Parameters:
        T: The Pydantic model type.

    **Feature: python-api-base-2025-generics-audit**
    **Validates: Requirements 20.1**
    """

    def __init__(self, model: type[T]) -> None:
        self._model = model
        self._field_types = self._extract_field_types()

    def _extract_field_types(self) -> dict[str, str]:
        """Extract field types from Pydantic model."""
        type_map = {
            str: "String",
            int: "Int",
            float: "Float",
            bool: "Boolean",
            list: "List",
        }
        fields = {}
        for name, field_info in self._model.model_fields.items():
            annotation = field_info.annotation
            graphql_type = type_map.get(annotation, "String")
            is_required = field_info.is_required()
            fields[name] = f"{graphql_type}{'!' if is_required else ''}"
        return fields

    def to_graphql_schema(self) -> str:
        """Generate GraphQL schema definition."""
        type_name = self._model.__name__
        fields_str = "\n  ".join(
            f"{name}: {gql_type}" for name, gql_type in self._field_types.items()
        )
        return f"type {type_name} {{\n  {fields_str}\n}}"
