"""Create user command and handler.

**Feature: architecture-restructuring-2025**
**Validates: Requirements 3.1**
"""

from dataclasses import dataclass

from core.base.command import BaseCommand
from core.base.result import Result, Ok, Err
from application.common.cqrs.handlers import CommandHandler
from domain.users.aggregates import UserAggregate
from domain.users.repositories import IUserRepository
from domain.users.services import UserDomainService

from core.shared.utils.ids import generate_ulid


@dataclass(frozen=True)
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
    ) -> None:
        self._repository = user_repository
        self._service = user_service

    async def handle(
        self, command: CreateUserCommand
    ) -> Result[UserAggregate, Exception]:
        """Handle create user command.

        Args:
            command: CreateUserCommand with user data.

        Returns:
            Result containing created UserAggregate or validation error.
        """
        # Check if email already exists
        existing = await self._repository.exists_by_email(command.email)
        if existing:
            return Err(ValueError("Email already registered"))

        # Validate email format
        is_valid, error = self._service.validate_email(command.email)
        if not is_valid:
            return Err(ValueError(error or "Invalid email format"))

        # Validate password strength
        is_strong, errors = self._service.validate_password_strength(command.password)
        if not is_strong:
            return Err(ValueError("; ".join(errors)))

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

        # Save user
        saved_user = await self._repository.save(user)

        return Ok(saved_user)
