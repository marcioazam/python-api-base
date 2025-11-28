"""Advanced Specification pattern with SQL generation.

**Feature: code-review-refactoring, Task 16.1: Refactor advanced_specification.py**
**Validates: Requirements 5.1**

Original: advanced_specification.py (471 lines)
Refactored: advanced_specification/ package

This module extends the basic Specification pattern with:
- Comparison operators for field-based specifications
- SQL condition generation for SQLAlchemy integration
- Fluent builder API for complex specifications
"""

from .base import BaseSpecification, TrueSpecification, FalseSpecification
from .combinators import CompositeSpecification, NotSpecification
from .enums import ComparisonOperator
from .field import FieldSpecification, FilterCriteria
from .builder import SpecificationBuilder
from .factories import (
    field_eq,
    field_ne,
    field_gt,
    field_ge,
    field_lt,
    field_le,
    field_in,
    field_like,
    field_between,
    field_is_null,
)

__all__ = [
    # Base
    "BaseSpecification",
    "TrueSpecification",
    "FalseSpecification",
    # Combinators
    "CompositeSpecification",
    "NotSpecification",
    # Enums
    "ComparisonOperator",
    # Field
    "FieldSpecification",
    "FilterCriteria",
    # Builder
    "SpecificationBuilder",
    # Factories
    "field_eq",
    "field_ne",
    "field_gt",
    "field_ge",
    "field_lt",
    "field_le",
    "field_in",
    "field_like",
    "field_between",
    "field_is_null",
]
