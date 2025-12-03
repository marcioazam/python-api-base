"""Validation middleware for CQRS command bus.

Provides automatic validation of commands before execution using
a decorator pattern with configurable validators.

**Feature: application-layer-improvements-2025**
**Validates: Requirements 2.3, 5.6**
"""

import logging
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable, Sequence
from typing import Any

from core.base.patterns.result import Err, Result

logger = logging.getLogger(__name__)


# =============================================================================
# Validation Error Types
# =============================================================================


class ValidationError(Exception):
    """Validation error with structured error details."""

    def __init__(
        self,
        message: str,
        errors: list[dict[str, Any]] | None = None,
    ) -> None:
        """Initialize validation error.

        Args:
            message: Error message.
            errors: List of validation errors with field details.
        """
        self.message = message
        self.errors = errors or []
        super().__init__(message)

    def __str__(self) -> str:
        if self.errors:
            error_details = "; ".join(
                f"{e.get('field', 'unknown')}: {e.get('message', 'invalid')}"
                for e in self.errors
            )
            return f"{self.message}: {error_details}"
        return self.message


# =============================================================================
# Validator Protocol
# =============================================================================


class Validator[TCommand](ABC):
    """Abstract base class for command validators.

    Type Parameters:
        TCommand: The command type to validate.
    """

    @abstractmethod
    def validate(self, command: TCommand) -> list[dict[str, Any]]:
        """Validate a command.

        Args:
            command: Command to validate.

        Returns:
            List of validation errors. Empty list if valid.
        """
        ...


class CompositeValidator[TCommand](Validator[TCommand]):
    """Combines multiple validators into one.

    Type Parameters:
        TCommand: The command type to validate.
    """

    def __init__(self, validators: Sequence[Validator[TCommand]]) -> None:
        """Initialize composite validator.

        Args:
            validators: List of validators to combine.
        """
        self._validators = validators

    def validate(self, command: TCommand) -> list[dict[str, Any]]:
        """Run all validators and collect errors.

        Args:
            command: Command to validate.

        Returns:
            Combined list of validation errors from all validators.
        """
        errors: list[dict[str, Any]] = []
        for validator in self._validators:
            errors.extend(validator.validate(command))
        return errors


# =============================================================================
# Validation Middleware
# =============================================================================


class ValidationMiddleware[TCommand, TResult]:
    """Middleware that validates commands before execution.

    Intercepts commands in the middleware chain and runs registered
    validators before passing to the next handler.

    Type Parameters:
        TCommand: The command type.
        TResult: The result type.

    Example:
        >>> validators = {CreateUserCommand: [EmailValidator(), PasswordValidator()]}
        >>> middleware = ValidationMiddleware(validators)
        >>> bus.add_middleware(middleware)
    """

    def __init__(
        self,
        validators: dict[type, list[Validator[Any]]],
        *,
        fail_fast: bool = False,
    ) -> None:
        """Initialize validation middleware.

        Args:
            validators: Mapping of command types to their validators.
            fail_fast: If True, stop on first validation error.
        """
        self._validators = validators
        self._fail_fast = fail_fast

    async def __call__(
        self,
        command: TCommand,
        next_handler: Callable[[TCommand], Awaitable[Result[TResult, Exception]]],
    ) -> Result[TResult, Exception]:
        """Validate command and call next handler if valid.

        Args:
            command: The command to validate and execute.
            next_handler: The next handler in the middleware chain.

        Returns:
            Result from next handler or Err with ValidationError.
        """
        command_type = type(command)
        validators = self._validators.get(command_type, [])

        if not validators:
            return await next_handler(command)

        # Run validation
        all_errors: list[dict[str, Any]] = []
        for validator in validators:
            errors = validator.validate(command)
            if errors:
                all_errors.extend(errors)
                if self._fail_fast:
                    break

        if all_errors:
            logger.debug(
                f"Validation failed for {command_type.__name__}: {len(all_errors)} errors",
                extra={
                    "command_type": command_type.__name__,
                    "error_count": len(all_errors),
                    "operation": "VALIDATION",
                },
            )
            return Err(
                ValidationError(
                    message=f"Validation failed for {command_type.__name__}",
                    errors=all_errors,
                )
            )

        logger.debug(f"Validation passed for {command_type.__name__}")
        return await next_handler(command)


# =============================================================================
# Common Validators
# =============================================================================


class RequiredFieldValidator[TCommand](Validator[TCommand]):
    """Validates that required fields are present and non-empty.

    Type Parameters:
        TCommand: The command type to validate.
    """

    def __init__(self, fields: Sequence[str]) -> None:
        """Initialize validator.

        Args:
            fields: List of required field names.
        """
        self._fields = fields

    def validate(self, command: TCommand) -> list[dict[str, Any]]:
        """Check required fields are present.

        Args:
            command: Command to validate.

        Returns:
            List of errors for missing fields.
        """
        errors: list[dict[str, Any]] = []
        for field in self._fields:
            value = getattr(command, field, None)
            if value is None or (isinstance(value, str) and not value.strip()):
                errors.append({
                    "field": field,
                    "message": f"{field} is required",
                    "code": "required",
                })
        return errors


class StringLengthValidator[TCommand](Validator[TCommand]):
    """Validates string field lengths.

    Type Parameters:
        TCommand: The command type to validate.
    """

    def __init__(
        self,
        field: str,
        min_length: int = 0,
        max_length: int | None = None,
    ) -> None:
        """Initialize validator.

        Args:
            field: Field name to validate.
            min_length: Minimum string length.
            max_length: Maximum string length.
        """
        self._field = field
        self._min_length = min_length
        self._max_length = max_length

    def validate(self, command: TCommand) -> list[dict[str, Any]]:
        """Check string length constraints.

        Args:
            command: Command to validate.

        Returns:
            List of errors for length violations.
        """
        errors: list[dict[str, Any]] = []
        value = getattr(command, self._field, None)

        if value is None:
            return errors

        if not isinstance(value, str):
            return errors

        if len(value) < self._min_length:
            errors.append({
                "field": self._field,
                "message": f"{self._field} must be at least {self._min_length} characters",
                "code": "min_length",
            })

        if self._max_length is not None and len(value) > self._max_length:
            errors.append({
                "field": self._field,
                "message": f"{self._field} must not exceed {self._max_length} characters",
                "code": "max_length",
            })

        return errors


class RangeValidator[TCommand](Validator[TCommand]):
    """Validates numeric field ranges.

    Type Parameters:
        TCommand: The command type to validate.
    """

    def __init__(
        self,
        field: str,
        min_value: float | None = None,
        max_value: float | None = None,
    ) -> None:
        """Initialize validator.

        Args:
            field: Field name to validate.
            min_value: Minimum allowed value.
            max_value: Maximum allowed value.
        """
        self._field = field
        self._min_value = min_value
        self._max_value = max_value

    def validate(self, command: TCommand) -> list[dict[str, Any]]:
        """Check numeric range constraints.

        Args:
            command: Command to validate.

        Returns:
            List of errors for range violations.
        """
        errors: list[dict[str, Any]] = []
        value = getattr(command, self._field, None)

        if value is None:
            return errors

        if not isinstance(value, (int, float)):
            return errors

        if self._min_value is not None and value < self._min_value:
            errors.append({
                "field": self._field,
                "message": f"{self._field} must be at least {self._min_value}",
                "code": "min_value",
            })

        if self._max_value is not None and value > self._max_value:
            errors.append({
                "field": self._field,
                "message": f"{self._field} must not exceed {self._max_value}",
                "code": "max_value",
            })

        return errors
