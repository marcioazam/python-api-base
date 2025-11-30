"""response_transformation configuration."""

from __future__ import annotations
from typing import Any, TYPE_CHECKING
from collections.abc import Callable

if TYPE_CHECKING:
    from .service import (
        Transformer,
        CompositeTransformer,
    )


class TransformationBuilder:
    """Fluent builder for transformations."""

    def __init__(self) -> None:
        self._transformers: list["Transformer[dict[str, Any], dict[str, Any]]"] = []

    def rename_fields(self, renames: dict[str, str]) -> "TransformationBuilder":
        """Add field rename transformation."""
        from .service import FieldRenameTransformer
        self._transformers.append(FieldRenameTransformer(renames))
        return self

    def remove_fields(self, fields: set[str]) -> "TransformationBuilder":
        """Add field removal transformation."""
        from .service import FieldRemoveTransformer
        self._transformers.append(FieldRemoveTransformer(fields))
        return self

    def add_fields(
        self, fields: dict[str, Any] | Callable[[dict[str, Any]], dict[str, Any]]
    ) -> "TransformationBuilder":
        """Add field addition transformation."""
        from .service import FieldAddTransformer
        self._transformers.append(FieldAddTransformer(fields))
        return self

    def transform_fields(
        self, transformers: dict[str, Callable[[Any], Any]]
    ) -> "TransformationBuilder":
        """Add field value transformation."""
        from .service import FieldTransformTransformer
        self._transformers.append(FieldTransformTransformer(transformers))
        return self

    def for_version(
        self, min_version: str | None = None, max_version: str | None = None
    ) -> "TransformationBuilder":
        """Wrap last transformer with version constraint."""
        from .service import VersionedTransformer
        if self._transformers:
            last = self._transformers.pop()
            versioned = VersionedTransformer(min_version, max_version, last)
            self._transformers.append(versioned)
        return self

    def for_clients(self, *client_types: str) -> "TransformationBuilder":
        """Wrap last transformer with client type constraint."""
        from .service import ClientTypeTransformer
        if self._transformers:
            last = self._transformers.pop()
            client_transformer = ClientTypeTransformer(set(client_types), last)
            self._transformers.append(client_transformer)
        return self

    def build(self) -> "CompositeTransformer":
        """Build the composite transformer."""
        from .service import CompositeTransformer
        return CompositeTransformer(self._transformers)
