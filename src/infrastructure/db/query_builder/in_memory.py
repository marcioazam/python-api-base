"""In-memory implementation of QueryBuilder for testing.

**Feature: infrastructure-code-review**
**Refactored: 2025 - Reduced _compare complexity from 17 to <10**
"""

import re
from collections.abc import Callable, Sequence
from typing import Any

from pydantic import BaseModel

from infrastructure.db.query_builder.builder import QueryBuilder, QueryResult
from infrastructure.db.query_builder.conditions import (
    ComparisonOperator,
    ConditionGroup,
    LogicalOperator,
    QueryCondition,
    SortDirection,
)

# Type alias for comparison functions
type ComparisonFn = Callable[[Any, Any], bool]


def _compare_between(value: Any, target: Any) -> bool:
    """Compare value is between target range."""
    low, high = target
    return value is not None and low <= value <= high


class InMemoryQueryBuilder[T: BaseModel](QueryBuilder[T]):
    """In-memory implementation of QueryBuilder for testing."""

    # Comparison strategy map - reduces cyclomatic complexity
    _COMPARATORS: dict[ComparisonOperator, ComparisonFn] = {
        ComparisonOperator.EQ: lambda v, t: v == t,
        ComparisonOperator.NE: lambda v, t: v != t,
        ComparisonOperator.GT: lambda v, t: v is not None and v > t,
        ComparisonOperator.GE: lambda v, t: v is not None and v >= t,
        ComparisonOperator.LT: lambda v, t: v is not None and v < t,
        ComparisonOperator.LE: lambda v, t: v is not None and v <= t,
        ComparisonOperator.IN: lambda v, t: v in t,
        ComparisonOperator.NOT_IN: lambda v, t: v not in t,
        ComparisonOperator.IS_NULL: lambda v, _: v is None,
        ComparisonOperator.IS_NOT_NULL: lambda v, _: v is not None,
        ComparisonOperator.BETWEEN: _compare_between,
        ComparisonOperator.CONTAINS: lambda v, t: t in str(v or ""),
        ComparisonOperator.STARTS_WITH: lambda v, t: str(v or "").startswith(t),
        ComparisonOperator.ENDS_WITH: lambda v, t: str(v or "").endswith(t),
    }

    def __init__(self, data: Sequence[T] | None = None) -> None:
        """Initialize with optional data source."""
        super().__init__()
        self._data: list[T] = list(data) if data else []

    def set_data(self, data: Sequence[T]) -> "InMemoryQueryBuilder[T]":
        """Set the data source."""
        self._data = list(data)
        return self

    def _create_sub_builder(self) -> "InMemoryQueryBuilder[T]":
        """Create a new instance for sub-queries."""
        return InMemoryQueryBuilder(self._data)

    def _evaluate_condition(self, item: T, condition: QueryCondition) -> bool:
        """Evaluate a single condition against an item."""
        value = getattr(item, condition.field, None)
        result = self._compare(value, condition.operator, condition.value)
        return not result if condition.negate else result

    def _compare(self, value: Any, op: ComparisonOperator, target: Any) -> bool:
        """Compare value using operator via strategy pattern.

        **Refactored: Complexity reduced from 17 to 4**
        """
        # Handle LIKE/ILIKE separately due to instance method dependency
        if op == ComparisonOperator.LIKE:
            return self._match_pattern(str(value or ""), target)
        if op == ComparisonOperator.ILIKE:
            return self._match_pattern(str(value or "").lower(), target.lower())

        comparator = self._COMPARATORS.get(op)
        return comparator(value, target) if comparator else False

    def _match_pattern(self, value: str, pattern: str) -> bool:
        """Match SQL LIKE pattern (% = any, _ = single char).

        Special regex characters are escaped to match literally,
        except for SQL wildcards % and _.
        """
        # Use placeholders for SQL wildcards before escaping
        placeholder_percent = "\x00PERCENT\x00"
        placeholder_underscore = "\x00UNDERSCORE\x00"

        # Replace SQL wildcards with placeholders
        temp = pattern.replace("%", placeholder_percent).replace(
            "_", placeholder_underscore
        )

        # Escape all special regex characters
        escaped = re.escape(temp)

        # Convert placeholders back to regex patterns
        regex = escaped.replace(placeholder_percent, ".*").replace(
            placeholder_underscore, "."
        )
        return bool(re.match(f"^{regex}$", value))

    def _evaluate_group(self, item: T, group: ConditionGroup) -> bool:
        """Evaluate a condition group against an item."""
        if group.is_empty():
            return True

        results = []
        for cond in group.conditions:
            if isinstance(cond, ConditionGroup):
                results.append(self._evaluate_group(item, cond))
            else:
                results.append(self._evaluate_condition(item, cond))

        if group.operator == LogicalOperator.AND:
            return all(results)
        elif group.operator == LogicalOperator.OR:
            return any(results)
        elif group.operator == LogicalOperator.NOT:
            return not all(results)
        return True

    def _filter_items(self, items: Sequence[T]) -> list[T]:
        """Filter items based on conditions and specification."""
        filtered = list(items)

        if not self._conditions.is_empty():
            filtered = [
                i for i in filtered if self._evaluate_group(i, self._conditions)
            ]

        if self._specification:
            filtered = [i for i in filtered if self._specification.is_satisfied_by(i)]

        if not self._options.include_deleted:
            filtered = [
                i for i in filtered if not (hasattr(i, "is_deleted") and i.is_deleted)
            ]

        return filtered

    def _sort_items(self, items: list[T]) -> list[T]:
        """Sort items based on sort clauses."""
        if not self._sort_clauses:
            return items

        for clause in reversed(self._sort_clauses):
            reverse = clause.direction == SortDirection.DESC
            items = sorted(
                items,
                key=lambda x: getattr(x, clause.field, None) or "",
                reverse=reverse,
            )
        return items

    async def execute(self) -> QueryResult[T]:
        """Execute the query and return results."""
        filtered = self._filter_items(self._data)
        total = len(filtered)

        sorted_items = self._sort_items(filtered)
        paginated = sorted_items[
            self._options.skip : self._options.skip + self._options.limit
        ]

        has_more = self._options.skip + len(paginated) < total

        return QueryResult(
            items=paginated,
            total=total,
            skip=self._options.skip,
            limit=self._options.limit,
            has_more=has_more,
        )

    async def first(self) -> T | None:
        """Execute query and return first result."""
        self._options.limit = 1
        result = await self.execute()
        return result.items[0] if result.items else None

    async def count(self) -> int:
        """Execute query and return count only."""
        filtered = self._filter_items(self._data)
        return len(filtered)
