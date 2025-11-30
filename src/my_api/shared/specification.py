"""Specification pattern implementation for composable business rules.

Uses PEP 695 type parameter syntax (Python 3.12+) for cleaner generic definitions.
"""

from abc import ABC, abstractmethod
from collections.abc import Callable


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
