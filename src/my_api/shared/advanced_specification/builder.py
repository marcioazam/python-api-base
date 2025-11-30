"""Fluent builder for creating complex specifications."""

from typing import Any

from .base import BaseSpecification
from .enums import ComparisonOperator
from .field import FieldSpecification


class SpecificationBuilder[T]:
    """Fluent builder for creating complex specifications.

    Example:
        >>> spec = (
        ...     SpecificationBuilder[User]()
        ...     .where("status", ComparisonOperator.EQ, "active")
        ...     .and_where("age", ComparisonOperator.GE, 18)
        ...     .or_where("role", ComparisonOperator.EQ, "admin")
        ...     .build()
        ... )
    """

    def __init__(self) -> None:
        """Initialize the builder with no specification."""
        self._spec: BaseSpecification[T] | None = None

    def where(
        self,
        field: str,
        operator: ComparisonOperator,
        value: Any,
    ) -> "SpecificationBuilder[T]":
        """Set the initial condition."""
        self._spec = FieldSpecification(field, operator, value)
        return self

    def and_where(
        self,
        field: str,
        operator: ComparisonOperator,
        value: Any,
    ) -> "SpecificationBuilder[T]":
        """Add an AND condition."""
        if self._spec is None:
            raise ValueError("Must call where() before and_where()")

        new_spec = FieldSpecification[T](field, operator, value)
        self._spec = self._spec.and_(new_spec)
        return self

    def or_where(
        self,
        field: str,
        operator: ComparisonOperator,
        value: Any,
    ) -> "SpecificationBuilder[T]":
        """Add an OR condition."""
        if self._spec is None:
            raise ValueError("Must call where() before or_where()")

        new_spec = FieldSpecification[T](field, operator, value)
        self._spec = self._spec.or_(new_spec)
        return self

    def and_spec(self, spec: BaseSpecification[T]) -> "SpecificationBuilder[T]":
        """Add an AND with an existing specification."""
        if self._spec is None:
            raise ValueError("Must call where() before and_spec()")

        self._spec = self._spec.and_(spec)
        return self

    def or_spec(self, spec: BaseSpecification[T]) -> "SpecificationBuilder[T]":
        """Add an OR with an existing specification."""
        if self._spec is None:
            raise ValueError("Must call where() before or_spec()")

        self._spec = self._spec.or_(spec)
        return self

    def not_(self) -> "SpecificationBuilder[T]":
        """Negate the current specification."""
        if self._spec is None:
            raise ValueError("Must call where() before not_()")

        self._spec = self._spec.not_()
        return self

    def build(self) -> BaseSpecification[T]:
        """Build and return the final specification."""
        if self._spec is None:
            raise ValueError("No specification built. Call where() first.")

        return self._spec
