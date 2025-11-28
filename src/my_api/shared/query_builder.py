"""Type-safe Query Builder for composable database queries.

This module has been refactored into a package for better maintainability.
All exports are re-exported from the package for backward compatibility.

See: src/my_api/shared/query_builder/
"""

# Re-export all public APIs for backward compatibility
from my_api.shared.query_builder import (
    ComparisonOperator,
    ConditionGroup,
    FieldAccessor,
    InMemoryQueryBuilder,
    LogicalOperator,
    QueryBuilder,
    QueryCondition,
    QueryOptions,
    QueryResult,
    SortClause,
    SortDirection,
    field_,
)

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
