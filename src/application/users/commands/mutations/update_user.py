"""Update user command and handler.

**Feature: architecture-restructuring-2025**
**Validates: Requirements 3.1**
"""

from dataclasses import dataclass

from application.common.cqrs.handlers import CommandHandler
from core.base.cqrs.command import BaseCommand
from core.base.patterns.result import Err, Ok, Result
from domain.users.aggregates import UserAggregate
from domain.users.repositories import IUserRepository


@dataclass(frozen=True, kw_only=True)
class UpdateUserCommand(BaseCommand):
    """Command to update user profile."""

    user_id: str
    username: str | None = None
    display_name: str | None = None


class UpdateUserHandler(CommandHandler[UpdateUserCommand, UserAggregate]):
    """Handler for UpdateUserCommand."""

    def __init__(self, user_repository: IUserRepository) -> None:
        self._repository = user_repository

    async def handle(
        self, command: UpdateUserCommand
    ) -> Result[UserAggregate, Exception]:
        """Handle update user command.

        Args:
            command: UpdateUserCommand with user data.

        Returns:
            Result containing updated UserAggregate or error.
        """
        try:
            # Get existing user
            user = await self._repository.get_by_id(command.user_id)
            if user is None:
                return Err(ValueError(f"User {command.user_id} not found"))

            # Update profile if any fields provided
            if command.username is not None or command.display_name is not None:
                user.update_profile(
                    username=command.username,
                    display_name=command.display_name,
                )

            # Save updated user
            updated_user = await self._repository.save(user)

            return Ok(updated_user)

        except Exception as e:
            return Err(e)
