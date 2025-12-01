"""Enums for advanced specification pattern."""

from enum import Enum


class ComparisonOperator(str, Enum):
    """Comparison operators for field specifications.

    Supports standard comparison operations that can be evaluated
    both in-memory and translated to SQL conditions.
    """

    EQ = "eq"  # Equal
    NE = "ne"  # Not equal
    GT = "gt"  # Greater than
    GE = "ge"  # Greater than or equal
    LT = "lt"  # Less than
    LE = "le"  # Less than or equal
    IN = "in"  # In collection
    LIKE = "like"  # SQL LIKE pattern
    BETWEEN = "between"  # Between two values
    IS_NULL = "is_null"  # Is null check
