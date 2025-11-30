"""Base specification classes."""

from abc import ABC, abstractmethod
from typing import Any


class BaseSpecification[T](ABC):
    """Abstract base specification with SQL generation support.

    Extends the basic Specification pattern with the ability to
    generate SQLAlchemy filter conditions.
    """

    @abstractmethod
    def is_satisfied_by(self, candidate: T) -> bool:
        """Check if the candidate satisfies this specification."""
        ...

    @abstractmethod
    def to_sql_condition(self, model_class: type) -> Any:
        """Generate SQLAlchemy filter condition."""
        ...

    def and_(self, other: "BaseSpecification[T]") -> "BaseSpecification[T]":
        """Combine with another specification using AND logic."""
        from .combinators import CompositeSpecification
        return CompositeSpecification(self, other, "and")

    def or_(self, other: "BaseSpecification[T]") -> "BaseSpecification[T]":
        """Combine with another specification using OR logic."""
        from .combinators import CompositeSpecification
        return CompositeSpecification(self, other, "or")

    def not_(self) -> "BaseSpecification[T]":
        """Negate this specification."""
        from .combinators import NotSpecification
        return NotSpecification(self)

    def __and__(self, other: "BaseSpecification[T]") -> "BaseSpecification[T]":
        """Support & operator for AND combination."""
        return self.and_(other)

    def __or__(self, other: "BaseSpecification[T]") -> "BaseSpecification[T]":
        """Support | operator for OR combination."""
        return self.or_(other)

    def __invert__(self) -> "BaseSpecification[T]":
        """Support ~ operator for NOT."""
        return self.not_()


class TrueSpecification[T](BaseSpecification[T]):
    """Specification that always returns True."""

    def is_satisfied_by(self, candidate: T) -> bool:
        return True

    def to_sql_condition(self, model_class: type) -> Any:
        from sqlalchemy import true
        return true()


class FalseSpecification[T](BaseSpecification[T]):
    """Specification that always returns False."""

    def is_satisfied_by(self, candidate: T) -> bool:
        return False

    def to_sql_condition(self, model_class: type) -> Any:
        from sqlalchemy import false
        return false()
