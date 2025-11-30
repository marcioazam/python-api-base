"""Abstract Query Builder base class.

Provides a fluent API for building queries with conditions,
sorting, pagination, and specification integration.
"""

from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, Self

from pydantic import BaseModel

from my_api.shared.query_builder.conditions import (
    ConditionGroup,
    LogicalOperator,
    QueryCondition,
    SortClause,
    SortDirection,
)
from my_api.shared.specification import Specification


@dataclass(slots=True)
class QueryOptions:
    """Options for query execution."""

    skip: int = 0
    limit: int = 100
    include_deleted: bool = False
    distinct: bool = False
    count_only: bool = False


@dataclass(slots=True)
class QueryResult[T]:
    """Result of a query execution."""

    items: Sequence[T]
    total: int
    skip: int
    limit: int
    has_more: bool

    @property
    def page(self) -> int:
        """Calculate current page number (1-indexed)."""
        if self.limit == 0:
            return 1
        return (self.skip // self.limit) + 1

    @property
    def total_pages(self) -> int:
        """Calculate total number of pages."""
        if self.limit == 0:
            return 1
        return (self.total + self.limit - 1) // self.limit


class QueryBuilder[T: BaseModel](ABC):
    """Abstract base class for type-safe query builders."""

    def __init__(self) -> None:
        """Initialize query builder."""
        self._conditions: ConditionGroup = ConditionGroup()
        self._sort_clauses: list[SortClause] = []
        self._options: QueryOptions = QueryOptions()
        self._select_fields: list[str] | None = None
        self._specification: Specification[T] | None = None

    def where(self, condition: QueryCondition) -> Self:
        """Add a WHERE condition."""
        self._conditions.add(condition)
        return self

    def and_where(self, condition: QueryCondition) -> Self:
        """Add an AND condition (alias for where)."""
        return self.where(condition)

    def or_where(self, condition: QueryCondition) -> Self:
        """Add an OR condition."""
        if self._conditions.is_empty():
            return self.where(condition)
        or_group = ConditionGroup(operator=LogicalOperator.OR)
        or_group.conditions = [*self._conditions.conditions, condition]
        self._conditions = or_group
        return self

    def where_group(
        self,
        builder_fn: Callable[["QueryBuilder[T]"], "QueryBuilder[T]"],
        operator: LogicalOperator = LogicalOperator.AND,
    ) -> Self:
        """Add a grouped condition."""
        sub_builder = self._create_sub_builder()
        builder_fn(sub_builder)
        group = ConditionGroup(
            conditions=sub_builder._conditions.conditions,
            operator=operator,
        )
        self._conditions.add(group)
        return self

    def with_specification(self, spec: Specification[T]) -> Self:
        """Apply a specification for filtering."""
        if self._specification is None:
            self._specification = spec
        else:
            self._specification = self._specification & spec
        return self

    def order_by(self, *clauses: SortClause) -> Self:
        """Add sort clauses."""
        self._sort_clauses.extend(clauses)
        return self

    def order_by_field(
        self, field: str, direction: SortDirection = SortDirection.ASC
    ) -> Self:
        """Add sort by field name."""
        self._sort_clauses.append(SortClause(field, direction))
        return self

    def skip(self, count: int) -> Self:
        """Set number of items to skip."""
        self._options.skip = max(0, count)
        return self

    def limit(self, count: int) -> Self:
        """Set maximum number of items to return."""
        self._options.limit = max(0, count)
        return self

    def page(self, page_number: int, page_size: int = 20) -> Self:
        """Set pagination by page number."""
        page_number = max(1, page_number)
        self._options.skip = (page_number - 1) * page_size
        self._options.limit = page_size
        return self

    def include_deleted(self, include: bool = True) -> Self:
        """Include soft-deleted items."""
        self._options.include_deleted = include
        return self

    def distinct(self, enabled: bool = True) -> Self:
        """Enable distinct results."""
        self._options.distinct = enabled
        return self

    def select(self, *fields: str) -> Self:
        """Select specific fields."""
        self._select_fields = list(fields)
        return self

    def count_only(self, enabled: bool = True) -> Self:
        """Only return count, not items."""
        self._options.count_only = enabled
        return self

    def reset(self) -> Self:
        """Reset all query parameters."""
        self._conditions = ConditionGroup()
        self._sort_clauses = []
        self._options = QueryOptions()
        self._select_fields = None
        self._specification = None
        return self

    def clone(self) -> "QueryBuilder[T]":
        """Create a copy of this query builder."""
        new_builder = self._create_sub_builder()
        new_builder._conditions = ConditionGroup(
            conditions=list(self._conditions.conditions),
            operator=self._conditions.operator,
        )
        new_builder._sort_clauses = list(self._sort_clauses)
        new_builder._options = QueryOptions(
            skip=self._options.skip,
            limit=self._options.limit,
            include_deleted=self._options.include_deleted,
            distinct=self._options.distinct,
            count_only=self._options.count_only,
        )
        new_builder._select_fields = (
            list(self._select_fields) if self._select_fields else None
        )
        new_builder._specification = self._specification
        return new_builder

    @abstractmethod
    def _create_sub_builder(self) -> "QueryBuilder[T]":
        """Create a new instance for sub-queries."""
        ...

    @abstractmethod
    async def execute(self) -> QueryResult[T]:
        """Execute the query and return results."""
        ...

    @abstractmethod
    async def first(self) -> T | None:
        """Execute query and return first result."""
        ...

    @abstractmethod
    async def count(self) -> int:
        """Execute query and return count only."""
        ...

    def to_dict(self) -> dict[str, Any]:
        """Convert query to dictionary representation."""
        return {
            "conditions": self._serialize_conditions(self._conditions),
            "sort": [s.to_dict() for s in self._sort_clauses],
            "options": {
                "skip": self._options.skip,
                "limit": self._options.limit,
                "include_deleted": self._options.include_deleted,
                "distinct": self._options.distinct,
                "count_only": self._options.count_only,
            },
            "select": self._select_fields,
        }

    def _serialize_conditions(self, group: ConditionGroup) -> dict[str, Any]:
        """Serialize condition group to dictionary."""
        serialized = []
        for cond in group.conditions:
            if isinstance(cond, ConditionGroup):
                serialized.append(self._serialize_conditions(cond))
            else:
                serialized.append(cond.to_dict())
        return {"operator": group.operator.value, "conditions": serialized}
