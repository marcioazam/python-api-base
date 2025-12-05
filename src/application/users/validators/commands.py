"""Validators for User command validation.

Provides composable validators for user commands with proper error handling.

**Feature: application-layer-improvements-2025**
**Validates: Requirements - Validation extraction from handlers**
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

from core.base.patterns.result import Err, Ok

if TYPE_CHECKING:
    from application.users.commands.create_user import CreateUserCommand
    from core.base.patterns.result import Result
    from domain.users.repositories import IUserRepository
    from domain.users.services import UserDomainService

logger = logging.getLogger(__name__)


# =============================================================================
# Validator Base
# =============================================================================


class CommandValidator[T](ABC):
    """Base validator for commands.

    Type Parameters:
        T: The command type to validate.
    """

    @abstractmethod
    async def validate(self, command: T) -> Result[None, ValueError]:
        """Validate command.

        Args:
            command: The command to validate.

        Returns:
            Ok(None) if valid, Err(ValueError) with error message if invalid.
        """
        ...


# =============================================================================
# User Command Validators
# =============================================================================


@dataclass
class ValidationError(ValueError):
    """Validation error with structured data."""

    message: str
    field: str | None = None
    code: str | None = None

    def __str__(self) -> str:
        return self.message


class EmailUniquenessValidator(CommandValidator["CreateUserCommand"]):
    """Validates that email is unique (not already registered).

    Example:
        >>> validator = EmailUniquenessValidator(user_repository)
        >>> result = await validator.validate(command)
        >>> match result:
        ...     case Ok(_):
        ...         print("Email is unique")
        ...     case Err(error):
        ...         print(f"Duplicate email: {error}")
    """

    def __init__(self, repository: IUserRepository) -> None:
        """Initialize email uniqueness validator.

        Args:
            repository: User repository for checking existence.
        """
        self._repository = repository

    async def validate(self, command: CreateUserCommand) -> Result[None, ValueError]:
        """Validate email uniqueness.

        Args:
            command: CreateUserCommand with email.

        Returns:
            Ok(None) if email is unique, Err(ValueError) if duplicate.
        """
        existing = await self._repository.exists_by_email(command.email)

        if existing:
            logger.warning(
                "duplicate_email_validation_failed",
                extra={
                    "email": command.email,
                    "validator": "EmailUniquenessValidator",
                    "error_code": "DUPLICATE_EMAIL",
                },
            )
            return Err(
                ValidationError(
                    message="Email already registered",
                    field="email",
                    code="DUPLICATE_EMAIL",
                )
            )

        return Ok(None)


class EmailFormatValidator(CommandValidator["CreateUserCommand"]):
    """Validates email format using domain service.

    Example:
        >>> validator = EmailFormatValidator(user_service)
        >>> result = await validator.validate(command)
    """

    def __init__(self, user_service: UserDomainService) -> None:
        """Initialize email format validator.

        Args:
            user_service: User domain service for email validation.
        """
        self._service = user_service

    async def validate(self, command: CreateUserCommand) -> Result[None, ValueError]:
        """Validate email format.

        Args:
            command: CreateUserCommand with email.

        Returns:
            Ok(None) if valid format, Err(ValueError) if invalid.
        """
        is_valid, error = self._service.validate_email(command.email)

        if not is_valid:
            logger.warning(
                "email_format_validation_failed",
                extra={
                    "email": command.email,
                    "validator": "EmailFormatValidator",
                    "error_code": "INVALID_EMAIL_FORMAT",
                    "error_message": error,
                },
            )
            return Err(
                ValidationError(
                    message=error or "Invalid email format",
                    field="email",
                    code="INVALID_EMAIL_FORMAT",
                )
            )

        return Ok(None)


class PasswordStrengthValidator(CommandValidator["CreateUserCommand"]):
    """Validates password strength using domain service.

    Example:
        >>> validator = PasswordStrengthValidator(user_service)
        >>> result = await validator.validate(command)
    """

    def __init__(self, user_service: UserDomainService) -> None:
        """Initialize password strength validator.

        Args:
            user_service: User domain service for password validation.
        """
        self._service = user_service

    async def validate(self, command: CreateUserCommand) -> Result[None, ValueError]:
        """Validate password strength.

        Args:
            command: CreateUserCommand with password.

        Returns:
            Ok(None) if strong password, Err(ValueError) with errors if weak.
        """
        is_strong, errors = self._service.validate_password_strength(command.password)

        if not is_strong:
            logger.warning(
                "password_strength_validation_failed",
                extra={
                    "email": command.email,
                    "validator": "PasswordStrengthValidator",
                    "error_code": "WEAK_PASSWORD",
                    "validation_errors": errors,
                },
            )
            return Err(
                ValidationError(
                    message="; ".join(errors),
                    field="password",
                    code="WEAK_PASSWORD",
                )
            )

        return Ok(None)


# =============================================================================
# Composite Validator
# =============================================================================


class CompositeUserValidator(CommandValidator["CreateUserCommand"]):
    """Composites multiple validators for Create User command.

    Runs validators in sequence and fails fast on first error.

    Example:
        >>> validator = CompositeUserValidator(
        ...     EmailUniquenessValidator(repository),
        ...     EmailFormatValidator(service),
        ...     PasswordStrengthValidator(service),
        ... )
        >>> result = await validator.validate(command)
    """

    def __init__(self, *validators: CommandValidator[CreateUserCommand]) -> None:
        """Initialize composite validator.

        Args:
            *validators: Validators to run in sequence.
        """
        self._validators = validators

    async def validate(self, command: CreateUserCommand) -> Result[None, ValueError]:
        """Run all validators in sequence.

        Fails fast on first validation error.

        Args:
            command: CreateUserCommand to validate.

        Returns:
            Ok(None) if all pass, Err(ValueError) on first failure.
        """
        for validator in self._validators:
            result = await validator.validate(command)

            if result.is_err():
                return result

        logger.debug(
            "composite_validation_passed",
            extra={
                "email": command.email,
                "validators_count": len(self._validators),
                "validator": "CompositeUserValidator",
            },
        )

        return Ok(None)


# =============================================================================
# Factory Function
# =============================================================================


def create_user_validator(
    repository: IUserRepository,
    user_service: UserDomainService,
) -> CompositeUserValidator:
    """Factory function to create composite validator for CreateUserCommand.

    Convenience function that creates properly ordered validators.

    Args:
        repository: User repository for uniqueness checks.
        user_service: User domain service for format/strength validation.

    Returns:
        CompositeUserValidator with all validators configured.

    Example:
        >>> validator = create_user_validator(repository, service)
        >>> result = await validator.validate(command)
    """
    return CompositeUserValidator(
        # Order matters - check cheapest validations first
        EmailFormatValidator(user_service),  # 1. Format (no DB call)
        EmailUniquenessValidator(repository),  # 2. Uniqueness (DB call)
        PasswordStrengthValidator(user_service),  # 3. Password (no DB call)
    )
