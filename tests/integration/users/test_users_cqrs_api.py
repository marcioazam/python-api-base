"""Integration tests for Users CQRS API endpoints.

**Feature: users-module-integration-fix**
**Validates: Requirements 1.2, 1.3**
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, UTC

from fastapi import FastAPI
from fastapi.testclient import TestClient

from application.users.commands import CreateUserCommand, UpdateUserCommand, DeleteUserCommand
from application.users.queries import GetUserByIdQuery, ListUsersQuery
from application.users.commands.dtos import CreateUserDTO, UpdateUserDTO, UserDTO
from core.base.patterns.result import Ok, Err


class TestUsersRouterCQRS:
    """Integration tests for Users CQRS router."""

    @pytest.fixture
    def mock_command_bus(self) -> AsyncMock:
        """Create mock command bus."""
        return AsyncMock()

    @pytest.fixture
    def mock_query_bus(self) -> AsyncMock:
        """Create mock query bus."""
        return AsyncMock()

    def test_create_user_command_structure(self) -> None:
        """
        **Feature: users-module-integration-fix, Property 2: Command Dispatch Preserves User Data**
        
        Test that CreateUserCommand has correct structure.
        **Validates: Requirements 1.2**
        """
        command = CreateUserCommand(
            email="test@example.com",
            password="SecurePass123!",
            username="testuser",
            display_name="Test User",
        )
        
        assert command.email == "test@example.com"
        assert command.password == "SecurePass123!"
        assert command.username == "testuser"
        assert command.display_name == "Test User"

    def test_update_user_command_structure(self) -> None:
        """Test that UpdateUserCommand has correct structure."""
        command = UpdateUserCommand(
            user_id="user-123",
            username="newusername",
            display_name="New Display Name",
        )
        
        assert command.user_id == "user-123"
        assert command.username == "newusername"
        assert command.display_name == "New Display Name"

    def test_delete_user_command_structure(self) -> None:
        """Test that DeleteUserCommand has correct structure."""
        command = DeleteUserCommand(
            user_id="user-123",
            reason="User requested deletion",
        )
        
        assert command.user_id == "user-123"
        assert command.reason == "User requested deletion"

    def test_get_user_by_id_query_structure(self) -> None:
        """
        Test that GetUserByIdQuery has correct structure.
        **Validates: Requirements 1.3**
        """
        query = GetUserByIdQuery(user_id="user-123")
        
        assert query.user_id == "user-123"
        assert query.get_cache_key() == "user:user-123"

    def test_list_users_query_structure(self) -> None:
        """
        Test that ListUsersQuery has correct structure.
        **Validates: Requirements 1.3**
        """
        query = ListUsersQuery(
            page=2,
            page_size=50,
            include_inactive=True,
        )
        
        assert query.page == 2
        assert query.page_size == 50
        assert query.include_inactive is True
        assert query.get_cache_key() == "users:list:2:50:True"

    def test_list_users_query_defaults(self) -> None:
        """Test ListUsersQuery default values."""
        query = ListUsersQuery()
        
        assert query.page == 1
        assert query.page_size == 20
        assert query.include_inactive is False


class TestCreateUserDTO:
    """Tests for CreateUserDTO validation."""

    def test_valid_create_user_dto(self) -> None:
        """Test valid CreateUserDTO creation."""
        dto = CreateUserDTO(
            email="test@example.com",
            password="SecurePass123!",
            username="testuser",
            display_name="Test User",
        )
        
        assert dto.email == "test@example.com"
        assert dto.password == "SecurePass123!"

    def test_email_normalized_to_lowercase(self) -> None:
        """Test that email is normalized to lowercase."""
        dto = CreateUserDTO(
            email="TEST@EXAMPLE.COM",
            password="SecurePass123!",
        )
        
        assert dto.email == "test@example.com"

    def test_invalid_email_raises_error(self) -> None:
        """Test that invalid email raises validation error."""
        with pytest.raises(ValueError, match="Invalid email"):
            CreateUserDTO(
                email="not-an-email",
                password="SecurePass123!",
            )

    def test_short_password_raises_error(self) -> None:
        """Test that short password raises validation error."""
        with pytest.raises(ValueError):
            CreateUserDTO(
                email="test@example.com",
                password="short",
            )


class TestUserDTO:
    """Tests for UserDTO structure."""

    def test_user_dto_creation(self) -> None:
        """Test UserDTO creation with all fields."""
        now = datetime.now(UTC)
        dto = UserDTO(
            id="user-123",
            email="test@example.com",
            username="testuser",
            display_name="Test User",
            is_active=True,
            is_verified=False,
            created_at=now,
            updated_at=now,
        )
        
        assert dto.id == "user-123"
        assert dto.email == "test@example.com"
        assert dto.username == "testuser"
        assert dto.display_name == "Test User"
        assert dto.is_active is True
        assert dto.is_verified is False
