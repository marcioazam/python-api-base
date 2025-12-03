"""Unit tests for CreateUserHandler.

**Feature: application-layer-testing**
**Validates: Requirements CreateUserHandler correctness**
"""

import pytest
from unittest.mock import AsyncMock, Mock
from datetime import datetime, UTC

from application.users.commands.create_user import CreateUserCommand, CreateUserHandler
from domain.users.aggregates import UserAggregate
from domain.users.repositories import IUserRepository
from domain.users.services import UserDomainService
from core.base.patterns.result import Ok, Err


class TestCreateUserHandler:
    """Unit tests for CreateUserHandler."""

    @pytest.fixture
    def mock_repository(self) -> AsyncMock:
        """Create mock user repository."""
        mock = AsyncMock(spec=IUserRepository)
        return mock

    @pytest.fixture
    def mock_domain_service(self) -> Mock:
        """Create mock user domain service."""
        mock = Mock(spec=UserDomainService)
        return mock

    @pytest.fixture
    def handler(
        self,
        mock_repository: AsyncMock,
        mock_domain_service: Mock,
    ) -> CreateUserHandler:
        """Create handler instance with mocked dependencies."""
        return CreateUserHandler(
            user_repository=mock_repository,
            user_service=mock_domain_service,
        )

    @pytest.mark.asyncio
    async def test_create_user_success(
        self,
        handler: CreateUserHandler,
        mock_repository: AsyncMock,
        mock_domain_service: Mock,
    ) -> None:
        """Test successful user creation.

        **Property: Command Handler Success Path**
        **Validates: Requirements 1.1**
        """
        # Arrange
        command = CreateUserCommand(
            email="test@example.com",
            password="StrongPassword123!",
            username="testuser",
            display_name="Test User",
        )

        # Setup mocks
        mock_repository.exists_by_email.return_value = False
        mock_domain_service.validate_email.return_value = (True, None)
        mock_domain_service.validate_password_strength.return_value = (True, [])
        mock_domain_service.hash_password.return_value = "hashed_password_123"

        created_user = UserAggregate.create(
            user_id="user-123",
            email="test@example.com",
            password_hash="hashed_password_123",
            username="testuser",
            display_name="Test User",
        )
        mock_repository.save.return_value = created_user

        # Act
        result = await handler.handle(command)

        # Assert
        assert result.is_ok()
        user = result.unwrap()
        assert user.email == "test@example.com"
        assert user.username == "testuser"
        assert user.display_name == "Test User"

        # Verify interactions
        mock_repository.exists_by_email.assert_called_once_with("test@example.com")
        mock_domain_service.validate_email.assert_called_once_with("test@example.com")
        mock_domain_service.validate_password_strength.assert_called_once_with(
            "StrongPassword123!"
        )
        mock_domain_service.hash_password.assert_called_once_with("StrongPassword123!")
        mock_repository.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_user_email_already_exists(
        self,
        handler: CreateUserHandler,
        mock_repository: AsyncMock,
    ) -> None:
        """Test user creation fails when email already exists.

        **Property: Duplicate Email Prevention**
        **Validates: Requirements 1.2**
        """
        # Arrange
        command = CreateUserCommand(
            email="existing@example.com",
            password="StrongPassword123!",
        )

        mock_repository.exists_by_email.return_value = True

        # Act
        result = await handler.handle(command)

        # Assert
        assert result.is_err()
        error = result.unwrap_err()
        assert "Email already registered" in str(error)

        # Should not call other services if email exists
        mock_repository.save.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_user_invalid_email_format(
        self,
        handler: CreateUserHandler,
        mock_repository: AsyncMock,
        mock_domain_service: Mock,
    ) -> None:
        """Test user creation fails with invalid email format.

        **Property: Email Validation**
        **Validates: Requirements 1.3**
        """
        # Arrange
        command = CreateUserCommand(
            email="invalid-email",
            password="StrongPassword123!",
        )

        mock_repository.exists_by_email.return_value = False
        mock_domain_service.validate_email.return_value = (False, "Invalid email format")

        # Act
        result = await handler.handle(command)

        # Assert
        assert result.is_err()
        error = result.unwrap_err()
        assert "Invalid email format" in str(error)

        # Should not save if validation fails
        mock_repository.save.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_user_weak_password(
        self,
        handler: CreateUserHandler,
        mock_repository: AsyncMock,
        mock_domain_service: Mock,
    ) -> None:
        """Test user creation fails with weak password.

        **Property: Password Strength Validation**
        **Validates: Requirements 1.4**
        """
        # Arrange
        command = CreateUserCommand(
            email="test@example.com",
            password="weak",
        )

        mock_repository.exists_by_email.return_value = False
        mock_domain_service.validate_email.return_value = (True, None)
        mock_domain_service.validate_password_strength.return_value = (
            False,
            ["Password too short", "Missing special characters"],
        )

        # Act
        result = await handler.handle(command)

        # Assert
        assert result.is_err()
        error = result.unwrap_err()
        error_msg = str(error)
        assert "Password too short" in error_msg
        assert "Missing special characters" in error_msg

        # Should not save if validation fails
        mock_repository.save.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_user_with_minimal_fields(
        self,
        handler: CreateUserHandler,
        mock_repository: AsyncMock,
        mock_domain_service: Mock,
    ) -> None:
        """Test user creation with only required fields.

        **Property: Optional Fields Handling**
        **Validates: Requirements 1.5**
        """
        # Arrange
        command = CreateUserCommand(
            email="minimal@example.com",
            password="StrongPassword123!",
        )

        # Setup mocks
        mock_repository.exists_by_email.return_value = False
        mock_domain_service.validate_email.return_value = (True, None)
        mock_domain_service.validate_password_strength.return_value = (True, [])
        mock_domain_service.hash_password.return_value = "hashed_password"

        created_user = UserAggregate.create(
            user_id="user-456",
            email="minimal@example.com",
            password_hash="hashed_password",
            username=None,
            display_name=None,
        )
        mock_repository.save.return_value = created_user

        # Act
        result = await handler.handle(command)

        # Assert
        assert result.is_ok()
        user = result.unwrap()
        assert user.email == "minimal@example.com"
        assert user.username is None
        assert user.display_name is None

    @pytest.mark.asyncio
    async def test_create_user_repository_failure(
        self,
        handler: CreateUserHandler,
        mock_repository: AsyncMock,
        mock_domain_service: Mock,
    ) -> None:
        """Test handler gracefully handles repository failures.

        **Property: Error Handling - Repository Failures**
        **Validates: Requirements 1.6**
        """
        # Arrange
        command = CreateUserCommand(
            email="test@example.com",
            password="StrongPassword123!",
        )

        mock_repository.exists_by_email.return_value = False
        mock_domain_service.validate_email.return_value = (True, None)
        mock_domain_service.validate_password_strength.return_value = (True, [])
        mock_domain_service.hash_password.return_value = "hashed"

        # Simulate repository failure
        mock_repository.save.side_effect = Exception("Database connection failed")

        # Act
        result = await handler.handle(command)

        # Assert
        assert result.is_err()
        error = result.unwrap_err()
        assert "Database connection failed" in str(error)
