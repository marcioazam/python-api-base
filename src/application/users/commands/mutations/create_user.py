"""Create user command and handler.

**Feature: architecture-restructuring-2025**
**Validates: Requirements 3.1**
"""

import logging
import time
from dataclasses import dataclass

from application.common.cqrs.handlers import CommandHandler
from application.users.validators import CompositeUserValidator
from core.base.cqrs.command import BaseCommand
from core.base.patterns.result import Ok, Result
from core.shared.utils.ids import generate_ulid
from domain.users.aggregates import UserAggregate
from domain.users.repositories import IUserRepository
from domain.users.services import UserDomainService

logger = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class CreateUserCommand(BaseCommand):
    """Command to create a new user."""

    email: str
    password: str
    username: str | None = None
    display_name: str | None = None


class CreateUserHandler(CommandHandler[CreateUserCommand, UserAggregate]):
    """Handler for CreateUserCommand."""

    def __init__(
        self,
        user_repository: IUserRepository,
        user_service: UserDomainService,
        validator: CompositeUserValidator,
    ) -> None:
        self._repository = user_repository
        self._service = user_service
        self._validator = validator

    async def handle(
        self, command: CreateUserCommand
    ) -> Result[UserAggregate, Exception]:
        """Handle create user command.

        Args:
            command: CreateUserCommand with user data.

        Returns:
            Result containing created UserAggregate or validation error.
        """
        start_time = time.perf_counter()

        logger.info(
            "command_started",
            extra={
                "command_type": "CreateUserCommand",
                "email": command.email,
                "has_username": command.username is not None,
                "operation": "CREATE_USER",
            },
        )

        try:
            # Validate command (composite validator with email uniqueness, format, password strength)
            validation_result = await self._validator.validate(command)
            if validation_result.is_err():
                return validation_result

            # Hash password
            password_hash = self._service.hash_password(command.password)

            # Create user aggregate
            user = UserAggregate.create(
                user_id=generate_ulid(),
                email=command.email,
                password_hash=password_hash,
                username=command.username,
                display_name=command.display_name,
            )

            logger.debug(
                "user_aggregate_created",
                extra={
                    "command_type": "CreateUserCommand",
                    "user_id": user.id,
                    "email": command.email,
                    "operation": "CREATE_USER",
                },
            )

            # Save user
            saved_user = await self._repository.save(user)

            duration_ms = (time.perf_counter() - start_time) * 1000

            logger.info(
                "command_completed",
                extra={
                    "command_type": "CreateUserCommand",
                    "user_id": saved_user.id,
                    "email": saved_user.email,
                    "duration_ms": duration_ms,
                    "operation": "CREATE_USER",
                    "status": "SUCCESS",
                },
            )

            return Ok(saved_user)

        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000

            logger.error(
                "command_failed",
                exc_info=True,
                extra={
                    "command_type": "CreateUserCommand",
                    "email": command.email,
                    "duration_ms": duration_ms,
                    "operation": "CREATE_USER",
                    "status": "ERROR",
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )
            raise
