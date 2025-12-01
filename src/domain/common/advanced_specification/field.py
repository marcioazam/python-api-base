"""Field-based specification implementation."""

import re
from dataclasses import dataclass
from typing import Any

from .base import BaseSpecification
from .enums import ComparisonOperator


@dataclass(frozen=True, slots=True)
class FilterCriteria:
    """Immutable filter criteria for specifications."""

    field: str
    operator: ComparisonOperator
    value: Any


class FieldSpecification[T](BaseSpecification[T]):
    """Specification based on a field comparison."""

    def __init__(
        self,
        field: str,
        operator: ComparisonOperator,
        value: Any,
    ) -> None:
        """Initialize field specification."""
        self._field = field
        self._operator = operator
        self._value = value
        self._criteria = FilterCriteria(field, operator, value)

    @property
    def criteria(self) -> FilterCriteria:
        """Get the filter criteria."""
        return self._criteria

    def is_satisfied_by(self, candidate: T) -> bool:
        """Check if candidate satisfies this field specification."""
        if not hasattr(candidate, self._field):
            raise ValueError(f"Field '{self._field}' not found on candidate")

        field_value = getattr(candidate, self._field)
        return self._evaluate(field_value)

    def _evaluate(self, field_value: Any) -> bool:
        """Evaluate the comparison."""
        op = self._operator
        val = self._value

        if op == ComparisonOperator.EQ:
            return field_value == val
        elif op == ComparisonOperator.NE:
            return field_value != val
        elif op == ComparisonOperator.GT:
            return field_value > val
        elif op == ComparisonOperator.GE:
            return field_value >= val
        elif op == ComparisonOperator.LT:
            return field_value < val
        elif op == ComparisonOperator.LE:
            return field_value <= val
        elif op == ComparisonOperator.IN:
            return field_value in val
        elif op == ComparisonOperator.LIKE:
            pattern = val.replace("%", ".*").replace("_", ".")
            return bool(re.match(f"^{pattern}$", str(field_value), re.IGNORECASE))
        elif op == ComparisonOperator.BETWEEN:
            low, high = val
            return low <= field_value <= high
        elif op == ComparisonOperator.IS_NULL:
            return (field_value is None) == val

        return False

    def _has_field(self, model_class: type, field: str) -> bool:
        """Check if model has the specified field."""
        if hasattr(model_class, field):
            attr = getattr(model_class, field)
            if hasattr(attr, "property") or hasattr(attr, "type"):
                return True
        if hasattr(model_class, "__dataclass_fields__"):
            return field in model_class.__dataclass_fields__
        if hasattr(model_class, "model_fields"):
            return field in model_class.model_fields
        if hasattr(model_class, "__annotations__"):
            return field in model_class.__annotations__
        return hasattr(model_class, field)

    def to_sql_condition(self, model_class: type) -> Any:
        """Generate SQLAlchemy filter condition."""
        if not self._has_field(model_class, self._field):
            raise ValueError(f"Field '{self._field}' not found on model")

        column = getattr(model_class, self._field, None)

        if column is None or not hasattr(column, "property"):
            from sqlalchemy import literal_column
            column = literal_column(self._field)

        op = self._operator
        val = self._value

        if op == ComparisonOperator.EQ:
            return column == val
        elif op == ComparisonOperator.NE:
            return column != val
        elif op == ComparisonOperator.GT:
            return column > val
        elif op == ComparisonOperator.GE:
            return column >= val
        elif op == ComparisonOperator.LT:
            return column < val
        elif op == ComparisonOperator.LE:
            return column <= val
        elif op == ComparisonOperator.IN:
            return column.in_(val)
        elif op == ComparisonOperator.LIKE:
            return column.like(val)
        elif op == ComparisonOperator.BETWEEN:
            low, high = val
            return column.between(low, high)
        elif op == ComparisonOperator.IS_NULL:
            return column.is_(None) if val else column.isnot(None)

        raise ValueError(f"Unknown operator: {op}")
