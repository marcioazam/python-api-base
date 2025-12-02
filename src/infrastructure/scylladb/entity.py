"""ScyllaDB entity base classes.

**Feature: observability-infrastructure**
**Requirement: R4 - Generic ScyllaDB Repository**
"""

from __future__ import annotations

from datetime import datetime, UTC
from typing import Any, ClassVar
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ScyllaDBEntity(BaseModel):
    """Base class for ScyllaDB entities.

    All entities stored in ScyllaDB should inherit from this class.
    Provides common fields, serialization, and table metadata.

    **Feature: observability-infrastructure**
    **Requirement: R4.2 - Entity Base Class**

    Example:
        >>> class User(ScyllaDBEntity):
        ...     __table_name__ = "users"
        ...     __primary_key__ = ["id"]
        ...
        ...     name: str
        ...     email: str
        ...
        >>> user = User(name="John", email="john@example.com")
    """

    # Table metadata (override in subclass)
    __table_name__: ClassVar[str] = ""
    __primary_key__: ClassVar[list[str]] = ["id"]
    __clustering_key__: ClassVar[list[str]] = []

    # Common fields
    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = {"extra": "allow"}

    @classmethod
    def table_name(cls) -> str:
        """Get table name."""
        if not cls.__table_name__:
            # Default to class name in snake_case
            name = cls.__name__
            return "".join(
                f"_{c.lower()}" if c.isupper() else c
                for c in name
            ).lstrip("_")
        return cls.__table_name__

    @classmethod
    def primary_key(cls) -> list[str]:
        """Get primary key columns."""
        return cls.__primary_key__

    @classmethod
    def clustering_key(cls) -> list[str]:
        """Get clustering key columns."""
        return cls.__clustering_key__

    @classmethod
    def columns(cls) -> dict[str, str]:
        """Get column definitions for table creation.

        Returns:
            Dict of column name to CQL type
        """
        type_mapping = {
            "str": "text",
            "int": "int",
            "float": "double",
            "bool": "boolean",
            "UUID": "uuid",
            "datetime": "timestamp",
            "date": "date",
            "time": "time",
            "bytes": "blob",
            "list": "list<text>",
            "dict": "map<text, text>",
            "set": "set<text>",
        }

        columns = {}
        for field_name, field_info in cls.model_fields.items():
            annotation = field_info.annotation
            type_name = getattr(annotation, "__name__", str(annotation))

            # Handle Optional types
            if hasattr(annotation, "__origin__"):
                args = getattr(annotation, "__args__", ())
                if args:
                    type_name = getattr(args[0], "__name__", str(args[0]))

            cql_type = type_mapping.get(type_name, "text")
            columns[field_name] = cql_type

        return columns

    def to_dict(self, exclude_none: bool = False) -> dict[str, Any]:
        """Convert entity to dict for CQL.

        Args:
            exclude_none: Whether to exclude None values

        Returns:
            Dictionary with CQL-compatible values
        """
        data = self.model_dump(mode="python")

        # Convert datetime to proper format
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value

        if exclude_none:
            data = {k: v for k, v in data.items() if v is not None}

        return data

    @classmethod
    def from_row(cls, row: Any) -> "ScyllaDBEntity":
        """Create entity from CQL row.

        Args:
            row: CQL result row (named tuple)

        Returns:
            Entity instance
        """
        if hasattr(row, "_asdict"):
            data = row._asdict()
        else:
            data = dict(row)

        return cls.model_validate(data)

    def get_primary_key_values(self) -> dict[str, Any]:
        """Get primary key column values.

        Returns:
            Dict of primary key columns to values
        """
        data = self.to_dict()
        pk_cols = self.primary_key() + self.clustering_key()
        return {col: data[col] for col in pk_cols if col in data}
