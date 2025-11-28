"""Convenience factory functions for creating specifications."""

from typing import Any

from .enums import ComparisonOperator
from .field import FieldSpecification


def field_eq(field: str, value: Any) -> FieldSpecification:
    """Create an equality specification."""
    return FieldSpecification(field, ComparisonOperator.EQ, value)


def field_ne(field: str, value: Any) -> FieldSpecification:
    """Create a not-equal specification."""
    return FieldSpecification(field, ComparisonOperator.NE, value)


def field_gt(field: str, value: Any) -> FieldSpecification:
    """Create a greater-than specification."""
    return FieldSpecification(field, ComparisonOperator.GT, value)


def field_ge(field: str, value: Any) -> FieldSpecification:
    """Create a greater-than-or-equal specification."""
    return FieldSpecification(field, ComparisonOperator.GE, value)


def field_lt(field: str, value: Any) -> FieldSpecification:
    """Create a less-than specification."""
    return FieldSpecification(field, ComparisonOperator.LT, value)


def field_le(field: str, value: Any) -> FieldSpecification:
    """Create a less-than-or-equal specification."""
    return FieldSpecification(field, ComparisonOperator.LE, value)


def field_in(field: str, values: list[Any]) -> FieldSpecification:
    """Create an IN specification."""
    return FieldSpecification(field, ComparisonOperator.IN, values)


def field_like(field: str, pattern: str) -> FieldSpecification:
    """Create a LIKE specification."""
    return FieldSpecification(field, ComparisonOperator.LIKE, pattern)


def field_between(field: str, low: Any, high: Any) -> FieldSpecification:
    """Create a BETWEEN specification."""
    return FieldSpecification(field, ComparisonOperator.BETWEEN, (low, high))


def field_is_null(field: str, is_null: bool = True) -> FieldSpecification:
    """Create an IS NULL specification."""
    return FieldSpecification(field, ComparisonOperator.IS_NULL, is_null)
