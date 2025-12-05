"""Delete (deactivate) user command and handler.

**Feature: architecture-restructuring-2025**
**Validates: Requirements 3.1**
"""

from dataclasses import dataclass

from application.common.cqrs.handlers import CommandHandler
from core.base.cqrs.command import BaseCommand
from core.base.patterns.result import Err, Ok, Result
from domain.users.repositories import IUserRepository


@dataclass(frozen=True, kw_only=True)
class DeleteUserCommand(BaseCommand):
    """Command to delete (deactivate) a user."""

    user_id: str
    reason: str = "User requested deletion"


class DeleteUserHandler(CommandHandler[DeleteUserCommand, bool]):
    """Handler for DeleteUserCommand.

    Performs soft delete by deactivating the user account
    rather than physically removing data.
    """

    def __init__(self, user_repository: IUserRepository) -> None:
        self._repository = user_repository

    async def handle(self, command: DeleteUserCommand) -> Result[bool, Exception]:
        """Handle delete user command.

        Args:
            command: DeleteUserCommand with user ID and reason.

        Returns:
            Result containing True if successful or error.
        """
        try:
            # Get existing user
            user = await self._repository.get_by_id(command.user_id)
            if user is None:
                return Err(ValueError(f"User {command.user_id} not found"))

            # Deactivate user (soft delete)
            user.deactivate(reason=command.reason)

            # Save deactivated user
            await self._repository.save(user)

            return Ok(True)

        except Exception as e:
            return Err(e)
