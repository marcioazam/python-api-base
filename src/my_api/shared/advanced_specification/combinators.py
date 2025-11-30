"""Specification combinators (AND, OR, NOT)."""

from typing import Any

from sqlalchemy import and_ as sql_and
from sqlalchemy import not_ as sql_not
from sqlalchemy import or_ as sql_or

from .base import BaseSpecification


class CompositeSpecification[T](BaseSpecification[T]):
    """Specification combining two specifications with AND/OR logic."""

    def __init__(
        self,
        left: BaseSpecification[T],
        right: BaseSpecification[T],
        operator: str,
    ) -> None:
        """Initialize composite specification.

        Args:
            left: Left specification.
            right: Right specification.
            operator: "and" or "or".
        """
        self._left = left
        self._right = right
        self._operator = operator

    def is_satisfied_by(self, candidate: T) -> bool:
        """Check if candidate satisfies the composite specification."""
        left_result = self._left.is_satisfied_by(candidate)
        right_result = self._right.is_satisfied_by(candidate)

        if self._operator == "and":
            return left_result and right_result
        return left_result or right_result

    def to_sql_condition(self, model_class: type) -> Any:
        """Generate SQLAlchemy filter condition."""
        left_cond = self._left.to_sql_condition(model_class)
        right_cond = self._right.to_sql_condition(model_class)

        if self._operator == "and":
            return sql_and(left_cond, right_cond)
        return sql_or(left_cond, right_cond)


class NotSpecification[T](BaseSpecification[T]):
    """Specification that negates another specification."""

    def __init__(self, spec: BaseSpecification[T]) -> None:
        """Initialize NOT specification."""
        self._spec = spec

    def is_satisfied_by(self, candidate: T) -> bool:
        """Check if candidate does NOT satisfy the specification."""
        return not self._spec.is_satisfied_by(candidate)

    def to_sql_condition(self, model_class: type) -> Any:
        """Generate SQLAlchemy NOT filter condition."""
        return sql_not(self._spec.to_sql_condition(model_class))
