"""Generic validation protocols and utilities.

Uses PEP 695 type parameter syntax (Python 3.12+) for cleaner generic definitions.

**Feature: python-api-base-2025-generics-audit**
**Validates: Requirements 10.1, 10.2, 10.5**
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Protocol, Self, runtime_checkable

from core.base.result import Err, Ok, Result


@dataclass(frozen=True, slots=True)
class FieldError:
    """Represents a validation error for a specific field.

    **Feature: python-api-base-2025-generics-audit**
    **Validates: Requirements 10.5**
    """

    field: str
    message: str
    code: str = "validation_error"
    value: object = None


@dataclass(frozen=True, slots=True)
class ValidationError[T]:
    """Generic validation error with typed context.

    Type Parameters:
        T: The type of the validated object.

    **Feature: python-api-base-2025-generics-audit**
    **Validates: Requirements 10.5**
    """

    message: str
    errors: list[FieldError] = field(default_factory=list)
    context: T | None = None

    def add_error(
        self, field: str, message: str, code: str = "validation_error"
    ) -> Self:
        """Add a field error (returns new instance due to immutability)."""
        new_errors = list(self.errors)
        new_errors.append(FieldError(field=field, message=message, code=code))
        return ValidationError(
            message=self.message,
            errors=new_errors,
            context=self.context,
        )

    @property
    def has_errors(self) -> bool:
        """Check if there are any field errors."""
        return len(self.errors) > 0

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "message": self.message,
            "errors": [
                {"field": e.field, "message": e.message, "code": e.code}
                for e in self.errors
            ],
        }


@runtime_checkable
class Validator[T](Protocol):
    """Generic validator protocol.

    Type Parameters:
        T: The type of object to validate.

    **Feature: python-api-base-2025-generics-audit**
    **Validates: Requirements 10.1**

    Example:
        >>> class EmailValidator(Validator[str]):
        ...     def validate(self, value: str) -> Result[str, ValidationError[str]]:
        ...         if "@" in value:
        ...             return Ok(value)
        ...         return Err(ValidationError("Invalid email", context=value))
    """

    def validate(self, value: T) -> Result[T, ValidationError[T]]:
        """Validate a value.

        Args:
            value: Value to validate.

        Returns:
            Ok with validated value or Err with validation error.
        """
        ...


class CompositeValidator[T](ABC):
    """Base class for composable validators.

    Allows chaining multiple validators together.

    **Feature: python-api-base-2025-generics-audit**
    **Validates: Requirements 10.2**
    """

    @abstractmethod
    def validate(self, value: T) -> Result[T, ValidationError[T]]:
        """Validate the value."""
        ...

    def and_then(self, other: "CompositeValidator[T]") -> "ChainedValidator[T]":
        """Chain with another validator (both must pass)."""
        return ChainedValidator([self, other])

    def or_else(self, other: "CompositeValidator[T]") -> "AlternativeValidator[T]":
        """Chain with alternative validator (either can pass)."""
        return AlternativeValidator([self, other])


class ChainedValidator[T](CompositeValidator[T]):
    """Validator that chains multiple validators (AND logic).

    All validators must pass for the result to be Ok.
    """

    def __init__(self, validators: list[CompositeValidator[T]]) -> None:
        self._validators = validators

    def validate(self, value: T) -> Result[T, ValidationError[T]]:
        """Run all validators in sequence."""
        current_value = value
        for validator in self._validators:
            result = validator.validate(current_value)
            if result.is_err():
                return result
            current_value = result.unwrap()
        return Ok(current_value)


class AlternativeValidator[T](CompositeValidator[T]):
    """Validator that tries alternatives (OR logic).

    At least one validator must pass for the result to be Ok.
    """

    def __init__(self, validators: list[CompositeValidator[T]]) -> None:
        self._validators = validators

    def validate(self, value: T) -> Result[T, ValidationError[T]]:
        """Run validators until one succeeds."""
        last_error: ValidationError[T] | None = None
        for validator in self._validators:
            result = validator.validate(value)
            if result.is_ok():
                return result
            last_error = result.error  # type: ignore
        return Err(last_error or ValidationError("All validators failed"))


class PredicateValidator[T](CompositeValidator[T]):
    """Validator based on a predicate function.

    Example:
        >>> validator = PredicateValidator(lambda x: x > 0, "Must be positive")
        >>> validator.validate(5)  # Ok(5)
        >>> validator.validate(-1)  # Err(ValidationError(...))
    """

    def __init__(
        self,
        predicate: Callable[[T], bool],
        error_message: str,
        error_code: str = "predicate_failed",
    ) -> None:
        self._predicate = predicate
        self._error_message = error_message
        self._error_code = error_code

    def validate(self, value: T) -> Result[T, ValidationError[T]]:
        """Validate using predicate."""
        if self._predicate(value):
            return Ok(value)
        return Err(
            ValidationError(
                message=self._error_message,
                errors=[
                    FieldError(
                        field="value",
                        message=self._error_message,
                        code=self._error_code,
                    )
                ],
                context=value,
            )
        )


class NotEmptyValidator(CompositeValidator[str]):
    """Validator that ensures string is not empty."""

    def validate(self, value: str) -> Result[str, ValidationError[str]]:
        if value and value.strip():
            return Ok(value)
        return Err(
            ValidationError(
                message="Value cannot be empty",
                errors=[
                    FieldError(
                        field="value",
                        message="Value cannot be empty",
                        code="empty_value",
                    )
                ],
                context=value,
            )
        )


class RangeValidator[T: (int, float)](CompositeValidator[T]):
    """Validator that ensures value is within a range."""

    def __init__(self, min_value: T | None = None, max_value: T | None = None) -> None:
        self._min = min_value
        self._max = max_value

    def validate(self, value: T) -> Result[T, ValidationError[T]]:
        if self._min is not None and value < self._min:
            return Err(
                ValidationError(
                    message=f"Value must be >= {self._min}",
                    errors=[
                        FieldError(
                            field="value",
                            message=f"Value must be >= {self._min}",
                            code="min_value",
                        )
                    ],
                    context=value,
                )
            )
        if self._max is not None and value > self._max:
            return Err(
                ValidationError(
                    message=f"Value must be <= {self._max}",
                    errors=[
                        FieldError(
                            field="value",
                            message=f"Value must be <= {self._max}",
                            code="max_value",
                        )
                    ],
                    context=value,
                )
            )
        return Ok(value)


def validate_all[T](
    value: T,
    validators: list[CompositeValidator[T]],
) -> Result[T, ValidationError[T]]:
    """Run all validators and collect all errors.

    Unlike ChainedValidator, this collects all errors instead of stopping at first.

    Args:
        value: Value to validate.
        validators: List of validators to run.

    Returns:
        Ok with value if all pass, Err with all collected errors.
    """
    all_errors: list[FieldError] = []

    for validator in validators:
        result = validator.validate(value)
        if result.is_err():
            error = result.error  # type: ignore
            all_errors.extend(error.errors)

    if all_errors:
        return Err(
            ValidationError(
                message="Validation failed",
                errors=all_errors,
                context=value,
            )
        )
    return Ok(value)
