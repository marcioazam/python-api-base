"""Specification pattern implementation for composable business rules.

Uses PEP 695 type parameter syntax (Python 3.12+) for cleaner generic definitions.
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from enum import Enum
from typing import Any


class Specification[T](ABC):
    """Abstract base class for specifications.

    A specification encapsulates a business rule that can be evaluated
    against a candidate object. Specifications can be combined using
    logical operators (and, or, not).
    """

    @abstractmethod
    def is_satisfied_by(self, candidate: T) -> bool:
        """Check if the candidate satisfies this specification.

        Args:
            candidate: Object to evaluate.

        Returns:
            bool: True if specification is satisfied.
        """
        ...

    def and_spec(self, other: "Specification[T]") -> "Specification[T]":
        """Combine with another specification using AND logic.

        Args:
            other: Specification to combine with.

        Returns:
            Specification: Combined specification.
        """
        return AndSpecification(self, other)

    def or_spec(self, other: "Specification[T]") -> "Specification[T]":
        """Combine with another specification using OR logic.

        Args:
            other: Specification to combine with.

        Returns:
            Specification: Combined specification.
        """
        return OrSpecification(self, other)

    def not_spec(self) -> "Specification[T]":
        """Negate this specification.

        Returns:
            Specification: Negated specification.
        """
        return NotSpecification(self)

    def __and__(self, other: "Specification[T]") -> "Specification[T]":
        """Support & operator for AND combination."""
        return self.and_spec(other)

    def __or__(self, other: "Specification[T]") -> "Specification[T]":
        """Support | operator for OR combination."""
        return self.or_spec(other)

    def __invert__(self) -> "Specification[T]":
        """Support ~ operator for NOT."""
        return self.not_spec()


class AndSpecification[T](Specification[T]):
    """Specification that combines two specifications with AND logic."""

    def __init__(self, left: Specification[T], right: Specification[T]) -> None:
        """Initialize AND specification.

        Args:
            left: First specification.
            right: Second specification.
        """
        self._left = left
        self._right = right

    def is_satisfied_by(self, candidate: T) -> bool:
        """Check if candidate satisfies both specifications.

        Args:
            candidate: Object to evaluate.

        Returns:
            bool: True if both specifications are satisfied.
        """
        return self._left.is_satisfied_by(candidate) and self._right.is_satisfied_by(
            candidate
        )


class OrSpecification[T](Specification[T]):
    """Specification that combines two specifications with OR logic."""

    def __init__(self, left: Specification[T], right: Specification[T]) -> None:
        """Initialize OR specification.

        Args:
            left: First specification.
            right: Second specification.
        """
        self._left = left
        self._right = right

    def is_satisfied_by(self, candidate: T) -> bool:
        """Check if candidate satisfies either specification.

        Args:
            candidate: Object to evaluate.

        Returns:
            bool: True if either specification is satisfied.
        """
        return self._left.is_satisfied_by(candidate) or self._right.is_satisfied_by(
            candidate
        )


class NotSpecification[T](Specification[T]):
    """Specification that negates another specification."""

    def __init__(self, spec: Specification[T]) -> None:
        """Initialize NOT specification.

        Args:
            spec: Specification to negate.
        """
        self._spec = spec

    def is_satisfied_by(self, candidate: T) -> bool:
        """Check if candidate does NOT satisfy the specification.

        Args:
            candidate: Object to evaluate.

        Returns:
            bool: True if specification is NOT satisfied.
        """
        return not self._spec.is_satisfied_by(candidate)


class PredicateSpecification[T](Specification[T]):
    """Specification based on a predicate function.

    This is a convenience class for creating specifications from
    simple predicate functions without subclassing.
    """

    def __init__(self, predicate: Callable[[T], bool], name: str = "") -> None:
        """Initialize predicate specification.

        Args:
            predicate: Function that takes candidate and returns bool.
            name: Optional name for debugging.
        """
        self._predicate = predicate
        self._name = name

    def is_satisfied_by(self, candidate: T) -> bool:
        """Check if candidate satisfies the predicate.

        Args:
            candidate: Object to evaluate.

        Returns:
            bool: Result of predicate function.
        """
        return self._predicate(candidate)

    def __repr__(self) -> str:
        """Return string representation."""
        return f"PredicateSpecification({self._name})"


def spec[T](predicate: Callable[[T], bool], name: str = "") -> Specification[T]:
    """Create a specification from a predicate function.

    Args:
        predicate: Function that takes candidate and returns bool.
        name: Optional name for debugging.

    Returns:
        Specification: Specification wrapping the predicate.

    Example:
        >>> is_adult = spec(lambda p: p.age >= 18, "is_adult")
        >>> is_active = spec(lambda p: p.status == "active", "is_active")
        >>> can_vote = is_adult.and_spec(is_active)
    """
    return PredicateSpecification(predicate, name)


class ComparisonOperator(Enum):
    """Comparison operators for AttributeSpecification."""

    EQ = "eq"
    NE = "ne"
    GT = "gt"
    GE = "ge"
    LT = "lt"
    LE = "le"
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    IN = "in"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"


class AttributeSpecification[T, V](Specification[T]):
    """Specification based on attribute comparison.

    A generic specification for comparing entity attributes using
    various comparison operators. Uses PEP 695 syntax.

    Type Parameters:
        T: The entity type being evaluated.
        V: The value type of the attribute being compared.

    Example:
        >>> age_spec = AttributeSpecification[User, int]("age", ComparisonOperator.GE, 18)
        >>> name_spec = AttributeSpecification[User, str](
        ...     "name", ComparisonOperator.STARTS_WITH, "J"
        ... )
        >>> combined = age_spec & name_spec
    """

    def __init__(
        self,
        attribute: str,
        operator: ComparisonOperator,
        value: V | None = None,
    ) -> None:
        """Initialize attribute specification.

        Args:
            attribute: Name of the attribute to compare.
            operator: Comparison operator to use.
            value: Value to compare against (not needed for IS_NULL/IS_NOT_NULL).
        """
        self._attribute = attribute
        self._operator = operator
        self._value = value

    @property
    def attribute(self) -> str:
        """Get the attribute name."""
        return self._attribute

    @property
    def operator(self) -> ComparisonOperator:
        """Get the comparison operator."""
        return self._operator

    @property
    def value(self) -> V | None:
        """Get the comparison value."""
        return self._value

    def is_satisfied_by(self, candidate: T) -> bool:
        """Check if candidate satisfies the attribute comparison.

        Args:
            candidate: Object to evaluate.

        Returns:
            bool: True if comparison is satisfied.
        """
        attr_value = getattr(candidate, self._attribute, None)

        match self._operator:
            case ComparisonOperator.EQ:
                return attr_value == self._value
            case ComparisonOperator.NE:
                return attr_value != self._value
            case ComparisonOperator.GT:
                return attr_value is not None and attr_value > self._value
            case ComparisonOperator.GE:
                return attr_value is not None and attr_value >= self._value
            case ComparisonOperator.LT:
                return attr_value is not None and attr_value < self._value
            case ComparisonOperator.LE:
                return attr_value is not None and attr_value <= self._value
            case ComparisonOperator.CONTAINS:
                return attr_value is not None and self._value in attr_value
            case ComparisonOperator.STARTS_WITH:
                return attr_value is not None and str(attr_value).startswith(
                    str(self._value)
                )
            case ComparisonOperator.ENDS_WITH:
                return attr_value is not None and str(attr_value).endswith(
                    str(self._value)
                )
            case ComparisonOperator.IN:
                return attr_value in (self._value or [])
            case ComparisonOperator.IS_NULL:
                return attr_value is None
            case ComparisonOperator.IS_NOT_NULL:
                return attr_value is not None
            case _:
                return False

    def to_expression(self) -> Any:
        """Convert to SQLAlchemy expression.

        Returns a tuple (attribute, operator, value) that can be used
        to build SQLAlchemy filters.

        Returns:
            Tuple of (attribute_name, operator, value) for SQLAlchemy integration.
        """
        return (self._attribute, self._operator.value, self._value)

    def __repr__(self) -> str:
        """Return string representation."""
        return f"AttributeSpecification({self._attribute} {self._operator.value} {self._value})"


# Convenience factory functions for common specifications
def equals[T, V](attribute: str, value: V) -> AttributeSpecification[T, V]:
    """Create an equality specification."""
    return AttributeSpecification(attribute, ComparisonOperator.EQ, value)


def not_equals[T, V](attribute: str, value: V) -> AttributeSpecification[T, V]:
    """Create a not-equal specification."""
    return AttributeSpecification(attribute, ComparisonOperator.NE, value)


def greater_than[T, V](attribute: str, value: V) -> AttributeSpecification[T, V]:
    """Create a greater-than specification."""
    return AttributeSpecification(attribute, ComparisonOperator.GT, value)


def less_than[T, V](attribute: str, value: V) -> AttributeSpecification[T, V]:
    """Create a less-than specification."""
    return AttributeSpecification(attribute, ComparisonOperator.LT, value)


def contains[T](attribute: str, value: str) -> AttributeSpecification[T, str]:
    """Create a contains specification for string attributes."""
    return AttributeSpecification(attribute, ComparisonOperator.CONTAINS, value)


def is_null[T](attribute: str) -> AttributeSpecification[T, None]:
    """Create an is-null specification."""
    return AttributeSpecification(attribute, ComparisonOperator.IS_NULL, None)


def is_not_null[T](attribute: str) -> AttributeSpecification[T, None]:
    """Create an is-not-null specification."""
    return AttributeSpecification(attribute, ComparisonOperator.IS_NOT_NULL, None)
