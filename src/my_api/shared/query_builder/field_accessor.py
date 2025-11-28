"""Type-safe field accessor for query building.

Enables IDE autocompletion and type checking for field references.
"""

from collections.abc import Sequence

from my_api.shared.query_builder.conditions import (
    ComparisonOperator,
    QueryCondition,
    SortClause,
    SortDirection,
)


class FieldAccessor[T, V]:
    """Type-safe field accessor for query building.

    Enables IDE autocompletion and type checking for field references.
    """

    def __init__(self, field_name: str, field_type: type[V] | None = None) -> None:
        """Initialize field accessor.

        Args:
            field_name: Name of the field.
            field_type: Type of the field value.
        """
        self._field_name = field_name
        self._field_type = field_type

    @property
    def name(self) -> str:
        """Get field name."""
        return self._field_name

    def eq(self, value: V) -> QueryCondition:
        """Create equality condition."""
        return QueryCondition(self._field_name, ComparisonOperator.EQ, value)

    def ne(self, value: V) -> QueryCondition:
        """Create not-equal condition."""
        return QueryCondition(self._field_name, ComparisonOperator.NE, value)

    def gt(self, value: V) -> QueryCondition:
        """Create greater-than condition."""
        return QueryCondition(self._field_name, ComparisonOperator.GT, value)

    def ge(self, value: V) -> QueryCondition:
        """Create greater-or-equal condition."""
        return QueryCondition(self._field_name, ComparisonOperator.GE, value)

    def lt(self, value: V) -> QueryCondition:
        """Create less-than condition."""
        return QueryCondition(self._field_name, ComparisonOperator.LT, value)

    def le(self, value: V) -> QueryCondition:
        """Create less-or-equal condition."""
        return QueryCondition(self._field_name, ComparisonOperator.LE, value)

    def in_(self, values: Sequence[V]) -> QueryCondition:
        """Create in-list condition."""
        return QueryCondition(self._field_name, ComparisonOperator.IN, list(values))

    def not_in(self, values: Sequence[V]) -> QueryCondition:
        """Create not-in-list condition."""
        return QueryCondition(self._field_name, ComparisonOperator.NOT_IN, list(values))

    def like(self, pattern: str) -> QueryCondition:
        """Create pattern match condition."""
        return QueryCondition(self._field_name, ComparisonOperator.LIKE, pattern)

    def ilike(self, pattern: str) -> QueryCondition:
        """Create case-insensitive pattern match condition."""
        return QueryCondition(self._field_name, ComparisonOperator.ILIKE, pattern)

    def is_null(self) -> QueryCondition:
        """Create is-null condition."""
        return QueryCondition(self._field_name, ComparisonOperator.IS_NULL, None)

    def is_not_null(self) -> QueryCondition:
        """Create is-not-null condition."""
        return QueryCondition(self._field_name, ComparisonOperator.IS_NOT_NULL, None)

    def between(self, low: V, high: V) -> QueryCondition:
        """Create between condition."""
        return QueryCondition(self._field_name, ComparisonOperator.BETWEEN, (low, high))

    def contains(self, value: str) -> QueryCondition:
        """Create contains condition."""
        return QueryCondition(self._field_name, ComparisonOperator.CONTAINS, value)

    def starts_with(self, value: str) -> QueryCondition:
        """Create starts-with condition."""
        return QueryCondition(self._field_name, ComparisonOperator.STARTS_WITH, value)

    def ends_with(self, value: str) -> QueryCondition:
        """Create ends-with condition."""
        return QueryCondition(self._field_name, ComparisonOperator.ENDS_WITH, value)

    def asc(self) -> SortClause:
        """Create ascending sort clause."""
        return SortClause(self._field_name, SortDirection.ASC)

    def desc(self) -> SortClause:
        """Create descending sort clause."""
        return SortClause(self._field_name, SortDirection.DESC)


def field_[T, V](name: str, field_type: type[V] | None = None) -> FieldAccessor[T, V]:
    """Create a type-safe field accessor.

    Args:
        name: Field name.
        field_type: Optional type hint for the field.

    Returns:
        FieldAccessor for building conditions.
    """
    return FieldAccessor(name, field_type)
