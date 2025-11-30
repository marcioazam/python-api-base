"""response_transformation service."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from collections.abc import Callable


@dataclass(frozen=True, slots=True)
class TransformationContext:
    """Context for transformation operations."""

    api_version: str = ""
    client_type: str = ""
    user_id: str = ""
    locale: str = "en"
    timezone: str = "UTC"
    metadata: dict[str, Any] = field(default_factory=dict)


class Transformer[InputT, OutputT](ABC):
    """Abstract base class for transformers."""

    @abstractmethod
    def transform(self, data: InputT, context: TransformationContext) -> OutputT:
        """Transform data based on context."""
        ...

    @abstractmethod
    def can_transform(self, context: TransformationContext) -> bool:
        """Check if this transformer applies to the context."""
        ...

class IdentityTransformer[T](Transformer[T, T]):
    """Transformer that returns data unchanged."""

    def transform(self, data: T, context: TransformationContext) -> T:
        return data

    def can_transform(self, context: TransformationContext) -> bool:
        return True

class FieldRenameTransformer(Transformer[dict[str, Any], dict[str, Any]]):
    """Transformer that renames fields."""

    def __init__(self, renames: dict[str, str]) -> None:
        self._renames = renames

    def transform(
        self, data: dict[str, Any], context: TransformationContext
    ) -> dict[str, Any]:
        result = {}
        for key, value in data.items():
            new_key = self._renames.get(key, key)
            result[new_key] = value
        return result

    def can_transform(self, context: TransformationContext) -> bool:
        return True

class FieldRemoveTransformer(Transformer[dict[str, Any], dict[str, Any]]):
    """Transformer that removes fields."""

    def __init__(self, fields_to_remove: set[str]) -> None:
        self._fields = fields_to_remove

    def transform(
        self, data: dict[str, Any], context: TransformationContext
    ) -> dict[str, Any]:
        return {k: v for k, v in data.items() if k not in self._fields}

    def can_transform(self, context: TransformationContext) -> bool:
        return True

class FieldAddTransformer(Transformer[dict[str, Any], dict[str, Any]]):
    """Transformer that adds fields."""

    def __init__(
        self, fields_to_add: dict[str, Any] | Callable[[dict[str, Any]], dict[str, Any]]
    ) -> None:
        self._fields = fields_to_add

    def transform(
        self, data: dict[str, Any], context: TransformationContext
    ) -> dict[str, Any]:
        result = dict(data)
        if callable(self._fields):
            result.update(self._fields(data))
        else:
            result.update(self._fields)
        return result

    def can_transform(self, context: TransformationContext) -> bool:
        return True

class FieldTransformTransformer(Transformer[dict[str, Any], dict[str, Any]]):
    """Transformer that transforms specific field values."""

    def __init__(
        self, field_transformers: dict[str, Callable[[Any], Any]]
    ) -> None:
        self._transformers = field_transformers

    def transform(
        self, data: dict[str, Any], context: TransformationContext
    ) -> dict[str, Any]:
        result = dict(data)
        for field_name, transformer in self._transformers.items():
            if field_name in result:
                result[field_name] = transformer(result[field_name])
        return result

    def can_transform(self, context: TransformationContext) -> bool:
        return True

class VersionedTransformer(Transformer[dict[str, Any], dict[str, Any]]):
    """Transformer that applies based on API version."""

    def __init__(
        self,
        min_version: str | None = None,
        max_version: str | None = None,
        transformer: Transformer[dict[str, Any], dict[str, Any]] | None = None,
    ) -> None:
        self._min_version = min_version
        self._max_version = max_version
        self._transformer = transformer or IdentityTransformer()

    def transform(
        self, data: dict[str, Any], context: TransformationContext
    ) -> dict[str, Any]:
        if self.can_transform(context):
            return self._transformer.transform(data, context)
        return data

    def can_transform(self, context: TransformationContext) -> bool:
        version = context.api_version
        if not version:
            return True

        if self._min_version and version < self._min_version:
            return False
        if self._max_version and version > self._max_version:
            return False
        return True

class ClientTypeTransformer(Transformer[dict[str, Any], dict[str, Any]]):
    """Transformer that applies based on client type."""

    def __init__(
        self,
        client_types: set[str],
        transformer: Transformer[dict[str, Any], dict[str, Any]] | None = None,
    ) -> None:
        self._client_types = client_types
        self._transformer = transformer or IdentityTransformer()

    def transform(
        self, data: dict[str, Any], context: TransformationContext
    ) -> dict[str, Any]:
        if self.can_transform(context):
            return self._transformer.transform(data, context)
        return data

    def can_transform(self, context: TransformationContext) -> bool:
        return context.client_type in self._client_types

class CompositeTransformer(Transformer[dict[str, Any], dict[str, Any]]):
    """Transformer that chains multiple transformers."""

    def __init__(
        self, transformers: list[Transformer[dict[str, Any], dict[str, Any]]] | None = None
    ) -> None:
        self._transformers = transformers or []

    def add(
        self, transformer: Transformer[dict[str, Any], dict[str, Any]]
    ) -> "CompositeTransformer":
        """Add a transformer to the chain."""
        self._transformers.append(transformer)
        return self

    def transform(
        self, data: dict[str, Any], context: TransformationContext
    ) -> dict[str, Any]:
        result = data
        for transformer in self._transformers:
            if transformer.can_transform(context):
                result = transformer.transform(result, context)
        return result

    def can_transform(self, context: TransformationContext) -> bool:
        return any(t.can_transform(context) for t in self._transformers)

class ResponseTransformer[T]:
    """Main response transformer with version and client support."""

    def __init__(self) -> None:
        self._transformers: list[Transformer[dict[str, Any], dict[str, Any]]] = []
        self._version_transformers: dict[str, Transformer[dict[str, Any], dict[str, Any]]] = {}
        self._client_transformers: dict[str, Transformer[dict[str, Any], dict[str, Any]]] = {}

    def add_transformer(
        self, transformer: Transformer[dict[str, Any], dict[str, Any]]
    ) -> "ResponseTransformer[T]":
        """Add a general transformer."""
        self._transformers.append(transformer)
        return self

    def for_version(
        self,
        version: str,
        transformer: Transformer[dict[str, Any], dict[str, Any]],
    ) -> "ResponseTransformer[T]":
        """Add a version-specific transformer."""
        self._version_transformers[version] = transformer
        return self

    def for_client(
        self,
        client_type: str,
        transformer: Transformer[dict[str, Any], dict[str, Any]],
    ) -> "ResponseTransformer[T]":
        """Add a client-specific transformer."""
        self._client_transformers[client_type] = transformer
        return self

    def transform(self, data: dict[str, Any], context: TransformationContext) -> dict[str, Any]:
        """Transform data based on context."""
        result = data

        # Apply general transformers
        for transformer in self._transformers:
            if transformer.can_transform(context):
                result = transformer.transform(result, context)

        # Apply version-specific transformer
        if context.api_version and context.api_version in self._version_transformers:
            transformer = self._version_transformers[context.api_version]
            result = transformer.transform(result, context)

        # Apply client-specific transformer
        if context.client_type and context.client_type in self._client_transformers:
            transformer = self._client_transformers[context.client_type]
            result = transformer.transform(result, context)

        return result

def snake_to_camel(name: str) -> str:
    """Convert snake_case to camelCase."""
    components = name.split("_")
    return components[0] + "".join(x.title() for x in components[1:])

def camel_to_snake(name: str) -> str:
    """Convert camelCase to snake_case."""
    result = []
    for char in name:
        if char.isupper():
            result.append("_")
            result.append(char.lower())
        else:
            result.append(char)
    return "".join(result).lstrip("_")

def convert_keys_to_camel(data: dict[str, Any]) -> dict[str, Any]:
    """Convert all keys in a dict to camelCase."""
    return {snake_to_camel(k): v for k, v in data.items()}

def convert_keys_to_snake(data: dict[str, Any]) -> dict[str, Any]:
    """Convert all keys in a dict to snake_case."""
    return {camel_to_snake(k): v for k, v in data.items()}

def format_datetime_iso(dt: datetime) -> str:
    """Format datetime as ISO string."""
    return dt.isoformat()

def format_datetime_unix(dt: datetime) -> int:
    """Format datetime as Unix timestamp."""
    return int(dt.timestamp())

def create_response_transformer() -> ResponseTransformer[Any]:
    """Create a new response transformer."""
    return ResponseTransformer()

def transform_for_version(
    data: dict[str, Any],
    version: str,
    transformations: dict[str, Transformer[dict[str, Any], dict[str, Any]]],
) -> dict[str, Any]:
    """Transform data based on version."""
    context = TransformationContext(api_version=version)
    transformer = transformations.get(version)
    if transformer:
        return transformer.transform(data, context)
    return data

def transform_for_client(
    data: dict[str, Any],
    client_type: str,
    transformations: dict[str, Transformer[dict[str, Any], dict[str, Any]]],
) -> dict[str, Any]:
    """Transform data based on client type."""
    context = TransformationContext(client_type=client_type)
    transformer = transformations.get(client_type)
    if transformer:
        return transformer.transform(data, context)
    return data
