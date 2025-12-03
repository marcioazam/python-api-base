"""Specification pattern for composable business rules.

**Feature: domain-consolidation-2025**
"""

from domain.common.specification.specification import (
    AndSpecification,
    AttributeSpecification,
    ComparisonOperator,
    NotSpecification,
    OrSpecification,
    PredicateSpecification,
    Specification,
    contains,
    equals,
    greater_than,
    is_not_null,
    is_null,
    less_than,
    not_equals,
    spec,
)

__all__ = [
    "AndSpecification",
    "AttributeSpecification",
    "ComparisonOperator",
    "NotSpecification",
    "OrSpecification",
    "PredicateSpecification",
    "Specification",
    "contains",
    "equals",
    "greater_than",
    "is_not_null",
    "is_null",
    "less_than",
    "not_equals",
    "spec",
]
