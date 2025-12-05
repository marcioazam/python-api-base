"""Validation middleware for CQRS command bus.

**Feature: application-layer-code-review-2025**
**Refactored: Split from validation.py for one-class-per-file compliance**
"""

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from application.common.errors import ValidationError
from application.common.middleware.validation.base import Validator
from core.base.patterns.result import Err, Result

logger = logging.getLogger(__name__)


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
