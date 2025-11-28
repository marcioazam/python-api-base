"""Type-safe Query Builder for composable database queries.

Provides a fluent API for building queries with full type safety,
integrating with the Specification pattern for filtering.

Uses PEP 695 type parameter syntax (Python 3.12+).
"""

from my_api.shared.query_builder.conditions import (
    ComparisonOperator,
    ConditionGroup,
    LogicalOperator,
    QueryCondition,
    SortClause,
    SortDirection,
)
from my_api.shared.query_builder.field_accessor import FieldAccessor, field_
from my_api.shared.query_builder.builder import (
    QueryBuilder,
    QueryOptions,
    QueryResult,
)
from my_api.shared.query_builder.in_memory import InMemoryQueryBuilder

__all__ = [
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
