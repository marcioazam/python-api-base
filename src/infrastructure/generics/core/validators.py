"""Shared validation utilities for infrastructure modules.

**Feature: infrastructure-generics-review-2025**
**Validates: Requirements 14.3**
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, TypeVar

from infrastructure.generics.errors import ErrorMessages, ValidationError

T = TypeVar("T")


@dataclass
class ValidationResult:
    """Result of a validation operation.

    Attributes:
        valid: Whether validation passed.
        errors: List of validation error messages.
    """

    valid: bool = True
    errors: list[str] = field(default_factory=list)

    def add_error(self, error: str) -> None:
        """Add a validation error."""
        self.errors.append(error)
        self.valid = False

    def merge(self, other: ValidationResult) -> ValidationResult:
        """Merge another validation result into this one."""
        if not other.valid:
            self.valid = False
            self.errors.extend(other.errors)
        return self


def validate_non_empty(
    value: str | None,
    field_name: str,
    raise_error: bool = True,
) -> ValidationResult:
    """Validate that a string value is not empty or whitespace.

    Args:
        value: The value to validate.
        field_name: Name of the field for error messages.
        raise_error: If True, raises ValidationError on failure.

    Returns:
        ValidationResult indicating success or failure.

    Raises:
        ValidationError: If raise_error is True and validation fails.
    """
    result = ValidationResult()

    if value is None or not value.strip():
        error_msg = ErrorMessages.format(
            ErrorMessages.VALIDATION_EMPTY_VALUE,
            field=field_name,
        )
        result.add_error(error_msg)

        if raise_error:
            raise ValidationError(error_msg, field=field_name)

    return result


def validate_range(
    value: int | float,
    field_name: str,
    min_value: int | float | None = None,
    max_value: int | float | None = None,
    raise_error: bool = True,
) -> ValidationResult:
    """Validate that a numeric value is within a range.

    Args:
        value: The value to validate.
        field_name: Name of the field for error messages.
        min_value: Minimum allowed value (inclusive).
        max_value: Maximum allowed value (inclusive).
        raise_error: If True, raises ValidationError on failure.

    Returns:
        ValidationResult indicating success or failure.

    Raises:
        ValidationError: If raise_error is True and validation fails.
    """
    result = ValidationResult()

    if min_value is not None and value < min_value:
        error_msg = ErrorMessages.format(
            ErrorMessages.VALIDATION_OUT_OF_RANGE,
            field=field_name,
            min=str(min_value),
            max=str(max_value or "∞"),
        )
        result.add_error(error_msg)

        if raise_error:
            raise ValidationError(error_msg, field=field_name)

    if max_value is not None and value > max_value:
        error_msg = ErrorMessages.format(
            ErrorMessages.VALIDATION_OUT_OF_RANGE,
            field=field_name,
            min=str(min_value or "-∞"),
            max=str(max_value),
        )
        result.add_error(error_msg)

        if raise_error:
            raise ValidationError(error_msg, field=field_name)

    return result


def validate_format(
    value: str,
    field_name: str,
    pattern: str,
    raise_error: bool = True,
) -> ValidationResult:
    """Validate that a string matches a regex pattern.

    Args:
        value: The value to validate.
        field_name: Name of the field for error messages.
        pattern: Regex pattern to match.
        raise_error: If True, raises ValidationError on failure.

    Returns:
        ValidationResult indicating success or failure.

    Raises:
        ValidationError: If raise_error is True and validation fails.
    """
    result = ValidationResult()

    if not re.match(pattern, value):
        error_msg = ErrorMessages.format(
            ErrorMessages.VALIDATION_PATTERN_MISMATCH,
            field=field_name,
            pattern=pattern,
        )
        result.add_error(error_msg)

        if raise_error:
            raise ValidationError(error_msg, field=field_name)

    return result


def validate_required(
    value: Any,
    field_name: str,
    raise_error: bool = True,
) -> ValidationResult:
    """Validate that a value is not None.

    Args:
        value: The value to validate.
        field_name: Name of the field for error messages.
        raise_error: If True, raises ValidationError on failure.

    Returns:
        ValidationResult indicating success or failure.

    Raises:
        ValidationError: If raise_error is True and validation fails.
    """
    result = ValidationResult()

    if value is None:
        error_msg = ErrorMessages.format(
            ErrorMessages.VALIDATION_REQUIRED,
            field=field_name,
        )
        result.add_error(error_msg)

        if raise_error:
            raise ValidationError(error_msg, field=field_name)

    return result
