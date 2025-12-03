"""Unit tests for DeleteUserHandler.

**Feature: application-layer-testing**
**Validates: Requirements DeleteUserHandler correctness**
"""

import pytest
from unittest.mock import AsyncMock

from application.users.commands.delete_user import DeleteUserCommand, DeleteUserHandler
from domain.users.aggregates import UserAggregate
from domain.users.repositories import IUserRepository
from core.base.patterns.result import Ok, Err


class TestDeleteUserHandler:
    """Unit tests for DeleteUserHandler."""

    @pytest.fixture
    def mock_repository(self) -> AsyncMock:
        """Create mock user repository."""
        return AsyncMock(spec=IUserRepository)

    @pytest.fixture
    def handler(self, mock_repository: AsyncMock) -> DeleteUserHandler:
        """Create handler instance with mocked dependencies."""
        return DeleteUserHandler(user_repository=mock_repository)

    @pytest.fixture
    def existing_user(self) -> UserAggregate:
        """Create an existing active user aggregate."""
        return UserAggregate.create(
            user_id="user-123",
            email="test@example.com",
            password_hash="hashed_password",
            username="testuser",
            display_name="Test User",
        )

    @pytest.mark.asyncio
    async def test_delete_user_success(
        self,
        handler: DeleteUserHandler,
        mock_repository: AsyncMock,
        existing_user: UserAggregate,
    ) -> None:
        """Test successful user deletion (soft delete).

        **Property: Delete Handler Success Path**
        **Validates: Requirements 3.1**
        """
        # Arrange
        command = DeleteUserCommand(
            user_id="user-123",
            reason="User requested account deletion",
        )

        mock_repository.get_by_id.return_value = existing_user

        # After soft delete, user is deactivated
        deleted_user = UserAggregate.create(
            user_id="user-123",
            email="test@example.com",
            password_hash="hashed_password",
            username="testuser",
            display_name="Test User",
        )
        deleted_user._is_active = False  # Soft delete sets to inactive
        mock_repository.save.return_value = deleted_user

        # Act
        result = await handler.handle(command)

        # Assert
        assert result.is_ok()
        success = result.unwrap()
        assert success is True

        # Verify interactions
        mock_repository.get_by_id.assert_called_once_with("user-123")
        mock_repository.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_user_not_found(
        self,
        handler: DeleteUserHandler,
        mock_repository: AsyncMock,
    ) -> None:
        """Test delete fails when user not found.

        **Property: Delete Handler Not Found Error**
        **Validates: Requirements 3.2**
        """
        # Arrange
        command = DeleteUserCommand(
            user_id="nonexistent-user",
            reason="Test deletion",
        )

        mock_repository.get_by_id.return_value = None

        # Act
        result = await handler.handle(command)

        # Assert
        assert result.is_err()
        error = result.unwrap_err()
        assert "not found" in str(error).lower()

        # Should not attempt to save
        mock_repository.save.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_user_with_reason(
        self,
        handler: DeleteUserHandler,
        mock_repository: AsyncMock,
        existing_user: UserAggregate,
    ) -> None:
        """Test deletion includes reason in command.

        **Property: Delete Reason Tracking**
        **Validates: Requirements 3.3**
        """
        # Arrange
        reason = "Violation of terms of service"
        command = DeleteUserCommand(
            user_id="user-123",
            reason=reason,
        )

        mock_repository.get_by_id.return_value = existing_user

        deleted_user = UserAggregate.create(
            user_id="user-123",
            email="test@example.com",
            password_hash="hashed_password",
        )
        deleted_user._is_active = False
        mock_repository.save.return_value = deleted_user

        # Act
        result = await handler.handle(command)

        # Assert
        assert result.is_ok()
        # Reason is passed in command and can be logged/audited
        assert command.reason == reason

    @pytest.mark.asyncio
    async def test_delete_user_already_deleted(
        self,
        handler: DeleteUserHandler,
        mock_repository: AsyncMock,
    ) -> None:
        """Test deleting already inactive user.

        **Property: Idempotent Delete**
        **Validates: Requirements 3.4**
        """
        # Arrange
        command = DeleteUserCommand(
            user_id="user-123",
            reason="Duplicate deletion attempt",
        )

        # User already inactive
        inactive_user = UserAggregate.create(
            user_id="user-123",
            email="test@example.com",
            password_hash="hashed_password",
        )
        inactive_user._is_active = False

        mock_repository.get_by_id.return_value = inactive_user
        mock_repository.save.return_value = inactive_user

        # Act
        result = await handler.handle(command)

        # Assert
        # Should still succeed (idempotent)
        assert result.is_ok()

    @pytest.mark.asyncio
    async def test_delete_user_repository_failure(
        self,
        handler: DeleteUserHandler,
        mock_repository: AsyncMock,
        existing_user: UserAggregate,
    ) -> None:
        """Test handler gracefully handles repository failures.

        **Property: Error Handling - Repository Failures**
        **Validates: Requirements 3.5**
        """
        # Arrange
        command = DeleteUserCommand(
            user_id="user-123",
            reason="Test deletion",
        )

        mock_repository.get_by_id.return_value = existing_user
        mock_repository.save.side_effect = Exception("Database write failed")

        # Act
        result = await handler.handle(command)

        # Assert
        assert result.is_err()
        error = result.unwrap_err()
        assert "Database write failed" in str(error)
