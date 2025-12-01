"""Create user command and handler.

**Feature: architecture-restructuring-2025**
**Validates: Requirements 3.1**
"""

from dataclasses import dataclass

from my_app.core.base.command import BaseCommand
from my_app.core.base.result import Result, Ok, Err
from my_app.application.common.handlers import CommandHandler
from my_app.domain.users.aggregates import UserAggregate
from my_app.domain.users.repositories import IUserRepository
from my_app.domain.users.services import UserDomainService

try:
    from my_app.shared.utils.ids import generate_ulid
except ImportError:
    import uuid
    def generate_ulid() -> str:
        return str(uuid.uuid4())


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
    
    async def handle(self, command: CreateUserCommand) -> Result[UserAggregate, Exception]:
        """Handle create user command."""
        try:
            # Check if email already exists
            existing = await self._repository.exists_by_email(command.email)
            if existing:
                return Err(ValueError(f"Email {command.email} already registered"))
            
            # Validate email
            is_valid, error = self._service.validate_email(command.email)
            if not is_valid:
                return Err(ValueError(error or "Invalid email"))
            
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
        except Exception as e:
            return Err(e)
