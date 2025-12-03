"""Generic Specification Pattern implementation.

Uses PEP 695 type parameter syntax (Python 3.12+) for cleaner generic definitions.

**Feature: python-api-architecture-2025**
**Validates: Requirements 11.1, 11.2, 11.3, 11.4, 11.5**
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any


class Specification[T](ABC):
    """Generic specification pattern for business rules.

    Encapsulates business rules that can be combined using boolean operators.
    Supports AND, OR, NOT composition for complex rule building.

    Type Parameters:
        T: The type of object this specification evaluates.

    Example:
        class ActiveUserSpec(Specification[User]):
            def is_satisfied_by(self, user: User) -> bool:
                return user.is_active and not user.is_deleted

        class PremiumUserSpec(Specification[User]):
            def is_satisfied_by(self, user: User) -> bool:
                return user.subscription_type == "premium"

        # Combine specifications
        active_premium = ActiveUserSpec() & PremiumUserSpec()
        users = [u for u in all_users if active_premium.is_satisfied_by(u)]
    """

    @abstractmethod
    def is_satisfied_by(self, candidate: T) -> bool:
        """Check if candidate satisfies this specification.

        Args:
            candidate: Object to evaluate.

        Returns:
            True if candidate satisfies the specification.
        """
        ...

    def __and__(self, other: "Specification[T]") -> "AndSpecification[T]":
        """Combine with AND operator."""
        return AndSpecification(self, other)

    def __or__(self, other: "Specification[T]") -> "OrSpecification[T]":
        """Combine with OR operator."""
        return OrSpecification(self, other)

    def __invert__(self) -> "NotSpecification[T]":
        """Negate with NOT operator."""
        return NotSpecification(self)


class CompositeSpecification[T](Specification[T]):
    """Base class for composite specifications."""

    pass


class AndSpecification[T](CompositeSpecification[T]):
    """Specification that combines two specs with AND logic.

    Both specifications must be satisfied for this to be satisfied.
    """

    def __init__(self, left: Specification[T], right: Specification[T]) -> None:
        """Initialize AND specification.

        Args:
            left: First specification.
            right: Second specification.
        """
        self._left = left
        self._right = right

    def is_satisfied_by(self, candidate: T) -> bool:
        """Check if candidate satisfies both specifications."""
        return self._left.is_satisfied_by(candidate) and self._right.is_satisfied_by(
            candidate
        )


class OrSpecification[T](CompositeSpecification[T]):
    """Specification that combines two specs with OR logic.

    At least one specification must be satisfied for this to be satisfied.
    """

    def __init__(self, left: Specification[T], right: Specification[T]) -> None:
        """Initialize OR specification.

        Args:
            left: First specification.
            right: Second specification.
        """
        self._left = left
        self._right = right

    def is_satisfied_by(self, candidate: T) -> bool:
        """Check if candidate satisfies at least one specification."""
        return self._left.is_satisfied_by(candidate) or self._right.is_satisfied_by(
            candidate
        )


class NotSpecification[T](CompositeSpecification[T]):
    """Specification that negates another specification.

    Satisfied when the wrapped specification is NOT satisfied.
    """

    def __init__(self, spec: Specification[T]) -> None:
        """Initialize NOT specification.

        Args:
            spec: Specification to negate.
        """
        self._spec = spec

    def is_satisfied_by(self, candidate: T) -> bool:
        """Check if candidate does NOT satisfy the wrapped specification."""
        return not self._spec.is_satisfied_by(candidate)


class TrueSpecification[T](Specification[T]):
    """Specification that always returns True."""

    def is_satisfied_by(self, candidate: T) -> bool:
        """Always returns True."""
        return True


class FalseSpecification[T](Specification[T]):
    """Specification that always returns False."""

    def is_satisfied_by(self, candidate: T) -> bool:
        """Always returns False."""
        return False


class PredicateSpecification[T](Specification[T]):
    """Specification based on a predicate function.

    Allows creating specifications from lambda or function references.
    """

    def __init__(self, predicate: "Callable[[T], bool]") -> None:
        """Initialize predicate specification.

        Args:
            predicate: Function that takes candidate and returns bool.
        """
        self._predicate = predicate

    def is_satisfied_by(self, candidate: T) -> bool:
        """Check if candidate satisfies the predicate."""
        return self._predicate(candidate)


class AttributeSpecification[T](Specification[T]):
    """Specification that checks an attribute value.

    Useful for simple attribute equality checks.
    """

    def __init__(self, attribute: str, value: Any) -> None:
        """Initialize attribute specification.

        Args:
            attribute: Name of attribute to check.
            value: Expected value.
        """
        self._attribute = attribute
        self._value = value

    def is_satisfied_by(self, candidate: T) -> bool:
        """Check if candidate's attribute equals expected value."""
        return getattr(candidate, self._attribute, None) == self._value
