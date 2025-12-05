"""Type-safe Query Builder for composable database queries.

Provides a fluent API for building queries with full type safety,
integrating with the Specification pattern for filtering.

Uses PEP 695 type parameter syntax (Python 3.12+).

Key Generic Types:
    - QueryBuilder[T: BaseModel]: Abstract query builder base
    - QueryResult[T]: Query execution result container
    - FieldAccessor[T, V]: Type-safe field reference for conditions

**Feature: architecture-validation-fixes-2025**
**Validates: Requirements 16.1, 16.2, 16.3, 16.4, 16.5**
"""

from infrastructure.db.query_builder.builder import (
    QueryBuilder,
    QueryOptions,
    QueryResult,
)
from infrastructure.db.query_builder.conditions import (
    ComparisonOperator,
    ConditionGroup,
    LogicalOperator,
    QueryCondition,
    SortClause,
    SortDirection,
)
from infrastructure.db.query_builder.field_accessor import FieldAccessor, field_
from infrastructure.db.query_builder.in_memory import InMemoryQueryBuilder
from infrastructure.db.query_builder.query_builder import build_query

__all__ = [
    "build_query",
    "ComparisonOperator",
    "ConditionGroup",
    "FieldAccessor",
    "InMemoryQueryBuilder",
    "LogicalOperator",
    "QueryBuilder",
    "QueryCondition",
    "QueryOptions",
    "QueryResult",
    "SortClause",
    "SortDirection",
    "field_",
]
