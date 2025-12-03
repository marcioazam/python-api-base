"""Unit tests for UpdateUserHandler.

**Feature: application-layer-testing**
**Validates: Requirements UpdateUserHandler correctness**
"""

import pytest
from unittest.mock import AsyncMock
from datetime import datetime, UTC

from application.users.commands.update_user import UpdateUserCommand, UpdateUserHandler
from domain.users.aggregates import UserAggregate
from domain.users.repositories import IUserRepository
from core.base.patterns.result import Ok, Err


class TestUpdateUserHandler:
    """Unit tests for UpdateUserHandler."""

    @pytest.fixture
    def mock_repository(self) -> AsyncMock:
        """Create mock user repository."""
        return AsyncMock(spec=IUserRepository)

    @pytest.fixture
    def handler(self, mock_repository: AsyncMock) -> UpdateUserHandler:
        """Create handler instance with mocked dependencies."""
        return UpdateUserHandler(user_repository=mock_repository)

    @pytest.fixture
    def existing_user(self) -> UserAggregate:
        """Create an existing user aggregate."""
        return UserAggregate.create(
            user_id="user-123",
            email="test@example.com",
            password_hash="hashed_password",
            username="oldusername",
            display_name="Old Name",
        )

    @pytest.mark.asyncio
    async def test_update_user_success(
        self,
        handler: UpdateUserHandler,
        mock_repository: AsyncMock,
        existing_user: UserAggregate,
    ) -> None:
        """Test successful user update.

        **Property: Update Handler Success Path**
        **Validates: Requirements 2.1**
        """
        # Arrange
        command = UpdateUserCommand(
            user_id="user-123",
            username="newusername",
            display_name="New Display Name",
        )

        mock_repository.get_by_id.return_value = existing_user

        updated_user = UserAggregate.create(
            user_id="user-123",
            email="test@example.com",
            password_hash="hashed_password",
            username="newusername",
            display_name="New Display Name",
        )
        mock_repository.save.return_value = updated_user

        # Act
        result = await handler.handle(command)

        # Assert
        assert result.is_ok()
        user = result.unwrap()
        assert user.username == "newusername"
        assert user.display_name == "New Display Name"

        # Verify interactions
        mock_repository.get_by_id.assert_called_once_with("user-123")
        mock_repository.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_user_not_found(
        self,
        handler: UpdateUserHandler,
        mock_repository: AsyncMock,
    ) -> None:
        """Test update fails when user not found.

        **Property: Update Handler Not Found Error**
        **Validates: Requirements 2.2**
        """
        # Arrange
        command = UpdateUserCommand(
            user_id="nonexistent-user",
            username="newusername",
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
    async def test_update_user_partial_update(
        self,
        handler: UpdateUserHandler,
        mock_repository: AsyncMock,
        existing_user: UserAggregate,
    ) -> None:
        """Test updating only username keeps display_name unchanged.

        **Property: Partial Update Preservation**
        **Validates: Requirements 2.3**
        """
        # Arrange
        command = UpdateUserCommand(
            user_id="user-123",
            username="newusername",
            display_name=None,  # Not updating display_name
        )

        mock_repository.get_by_id.return_value = existing_user

        # Create updated user with only username changed
        updated_user = UserAggregate.create(
            user_id="user-123",
            email="test@example.com",
            password_hash="hashed_password",
            username="newusername",
            display_name="Old Name",  # Preserved
        )
        mock_repository.save.return_value = updated_user

        # Act
        result = await handler.handle(command)

        # Assert
        assert result.is_ok()
        user = result.unwrap()
        assert user.username == "newusername"
        # Display name should be preserved (not None)
        assert user.display_name == "Old Name"

    @pytest.mark.asyncio
    async def test_update_user_repository_failure(
        self,
        handler: UpdateUserHandler,
        mock_repository: AsyncMock,
        existing_user: UserAggregate,
    ) -> None:
        """Test handler gracefully handles repository failures.

        **Property: Error Handling - Repository Failures**
        **Validates: Requirements 2.4**
        """
        # Arrange
        command = UpdateUserCommand(
            user_id="user-123",
            username="newusername",
        )

        mock_repository.get_by_id.return_value = existing_user
        mock_repository.save.side_effect = Exception("Database error")

        # Act
        result = await handler.handle(command)

        # Assert
        assert result.is_err()
        error = result.unwrap_err()
        assert "Database error" in str(error)

    @pytest.mark.asyncio
    async def test_update_user_with_empty_fields(
        self,
        handler: UpdateUserHandler,
        mock_repository: AsyncMock,
        existing_user: UserAggregate,
    ) -> None:
        """Test update with None values keeps original data.

        **Property: Null Update Preservation**
        **Validates: Requirements 2.5**
        """
        # Arrange
        command = UpdateUserCommand(
            user_id="user-123",
            username=None,
            display_name=None,
        )

        mock_repository.get_by_id.return_value = existing_user
        mock_repository.save.return_value = existing_user

        # Act
        result = await handler.handle(command)

        # Assert
        assert result.is_ok()
        user = result.unwrap()
        # Original values preserved
        assert user.username == "oldusername"
        assert user.display_name == "Old Name"
