"""Query conditions and sorting types for Query Builder.

Contains enums and dataclasses for query conditions, operators,
and sort clauses.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SortDirection(Enum):
    """Sort direction for query ordering."""

    ASC = "asc"
    DESC = "desc"


class ComparisonOperator(Enum):
    """Comparison operators for query conditions."""

    EQ = "eq"  # Equal
    NE = "ne"  # Not equal
    GT = "gt"  # Greater than
    GE = "ge"  # Greater or equal
    LT = "lt"  # Less than
    LE = "le"  # Less or equal
    IN = "in"  # In list
    NOT_IN = "not_in"  # Not in list
    LIKE = "like"  # Pattern match
    ILIKE = "ilike"  # Case-insensitive pattern match
    IS_NULL = "is_null"  # Is null
    IS_NOT_NULL = "is_not_null"  # Is not null
    BETWEEN = "between"  # Between two values
    CONTAINS = "contains"  # Contains substring
    STARTS_WITH = "starts_with"  # Starts with
    ENDS_WITH = "ends_with"  # Ends with


class LogicalOperator(Enum):
    """Logical operators for combining conditions."""

    AND = "and"
    OR = "or"
    NOT = "not"


@dataclass(frozen=True, slots=True)
class QueryCondition:
    """Represents a single query condition."""

    field: str
    operator: ComparisonOperator
    value: Any
    negate: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert condition to dictionary representation."""
        return {
            "field": self.field,
            "operator": self.operator.value,
            "value": self.value,
            "negate": self.negate,
        }


@dataclass(frozen=True, slots=True)
class SortClause:
    """Represents a sort clause."""

    field: str
    direction: SortDirection = SortDirection.ASC

    def to_dict(self) -> dict[str, str]:
        """Convert sort clause to dictionary."""
        return {"field": self.field, "direction": self.direction.value}


@dataclass(slots=True)
class ConditionGroup:
    """Group of conditions combined with a logical operator."""

    conditions: list[QueryCondition | "ConditionGroup"] = field(default_factory=list)
    operator: LogicalOperator = LogicalOperator.AND

    def add(self, condition: QueryCondition | "ConditionGroup") -> None:
        """Add a condition to the group."""
        self.conditions.append(condition)

    def is_empty(self) -> bool:
        """Check if group has no conditions."""
        return len(self.conditions) == 0
