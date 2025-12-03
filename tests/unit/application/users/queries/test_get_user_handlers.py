"""Unit tests for GetUser Query Handlers.

**Feature: application-layer-testing**
**Validates: Requirements Query Handler correctness**
"""

import pytest
from unittest.mock import AsyncMock
from datetime import datetime, UTC

from application.users.queries.get_user import (
    GetUserByIdQuery,
    GetUserByIdHandler,
    GetUserByEmailQuery,
    GetUserByEmailHandler,
    ListUsersQuery,
    ListUsersHandler,
)
from domain.users.aggregates import UserAggregate
from domain.users.repositories import IUserRepository, IUserReadRepository
from core.base.patterns.result import Ok, Err


class TestGetUserByIdHandler:
    """Unit tests for GetUserByIdHandler."""

    @pytest.fixture
    def mock_repository(self) -> AsyncMock:
        """Create mock user repository."""
        return AsyncMock(spec=IUserRepository)

    @pytest.fixture
    def handler(self, mock_repository: AsyncMock) -> GetUserByIdHandler:
        """Create handler instance with mocked dependencies."""
        return GetUserByIdHandler(repository=mock_repository)

    @pytest.mark.asyncio
    async def test_get_user_by_id_found(
        self,
        handler: GetUserByIdHandler,
        mock_repository: AsyncMock,
    ) -> None:
        """Test successful user retrieval by ID.

        **Property: Query Handler Success Path**
        **Validates: Requirements 4.1**
        """
        # Arrange
        query = GetUserByIdQuery(user_id="user-123")

        user = UserAggregate.create(
            user_id="user-123",
            email="test@example.com",
            password_hash="hashed",
            username="testuser",
        )
        mock_repository.get_by_id.return_value = user

        # Act
        result = await handler.handle(query)

        # Assert
        assert result.is_ok()
        user_data = result.unwrap()
        assert user_data is not None
        assert user_data["id"] == "user-123"
        assert user_data["email"] == "test@example.com"
        assert user_data["username"] == "testuser"

        mock_repository.get_by_id.assert_called_once_with("user-123")

    @pytest.mark.asyncio
    async def test_get_user_by_id_not_found(
        self,
        handler: GetUserByIdHandler,
        mock_repository: AsyncMock,
    ) -> None:
        """Test user not found returns None.

        **Property: Query Handler Not Found**
        **Validates: Requirements 4.2**
        """
        # Arrange
        query = GetUserByIdQuery(user_id="nonexistent")

        mock_repository.get_by_id.return_value = None

        # Act
        result = await handler.handle(query)

        # Assert
        assert result.is_ok()
        user_data = result.unwrap()
        assert user_data is None

    @pytest.mark.asyncio
    async def test_get_user_by_id_cache_key(self) -> None:
        """Test query generates correct cache key.

        **Property: Cache Key Generation**
        **Validates: Requirements 4.3**
        """
        # Arrange
        query = GetUserByIdQuery(user_id="user-456")

        # Act
        cache_key = query.get_cache_key()

        # Assert
        assert cache_key == "user:user-456"

    @pytest.mark.asyncio
    async def test_get_user_by_id_repository_failure(
        self,
        handler: GetUserByIdHandler,
        mock_repository: AsyncMock,
    ) -> None:
        """Test handler gracefully handles repository failures.

        **Property: Error Handling - Repository Failures**
        **Validates: Requirements 4.4**
        """
        # Arrange
        query = GetUserByIdQuery(user_id="user-123")

        mock_repository.get_by_id.side_effect = Exception("Database read failed")

        # Act
        result = await handler.handle(query)

        # Assert
        assert result.is_err()
        error = result.unwrap_err()
        assert "Database read failed" in str(error)


class TestGetUserByEmailHandler:
    """Unit tests for GetUserByEmailHandler."""

    @pytest.fixture
    def mock_repository(self) -> AsyncMock:
        """Create mock user repository."""
        return AsyncMock(spec=IUserRepository)

    @pytest.fixture
    def handler(self, mock_repository: AsyncMock) -> GetUserByEmailHandler:
        """Create handler instance with mocked dependencies."""
        return GetUserByEmailHandler(repository=mock_repository)

    @pytest.mark.asyncio
    async def test_get_user_by_email_found(
        self,
        handler: GetUserByEmailHandler,
        mock_repository: AsyncMock,
    ) -> None:
        """Test successful user retrieval by email.

        **Property: Query Handler Email Lookup**
        **Validates: Requirements 4.5**
        """
        # Arrange
        query = GetUserByEmailQuery(email="test@example.com")

        user = UserAggregate.create(
            user_id="user-789",
            email="test@example.com",
            password_hash="hashed",
        )
        mock_repository.get_by_email.return_value = user

        # Act
        result = await handler.handle(query)

        # Assert
        assert result.is_ok()
        user_data = result.unwrap()
        assert user_data is not None
        assert user_data["email"] == "test@example.com"

        mock_repository.get_by_email.assert_called_once_with("test@example.com")

    @pytest.mark.asyncio
    async def test_get_user_by_email_cache_key(self) -> None:
        """Test query generates correct cache key.

        **Property: Cache Key Generation for Email**
        **Validates: Requirements 4.6**
        """
        # Arrange
        query = GetUserByEmailQuery(email="user@domain.com")

        # Act
        cache_key = query.get_cache_key()

        # Assert
        assert cache_key == "user:email:user@domain.com"


class TestListUsersHandler:
    """Unit tests for ListUsersHandler."""

    @pytest.fixture
    def mock_read_repository(self) -> AsyncMock:
        """Create mock user read repository."""
        return AsyncMock(spec=IUserReadRepository)

    @pytest.fixture
    def handler(self, mock_read_repository: AsyncMock) -> ListUsersHandler:
        """Create handler instance with mocked dependencies."""
        return ListUsersHandler(read_repository=mock_read_repository)

    @pytest.mark.asyncio
    async def test_list_users_with_defaults(
        self,
        handler: ListUsersHandler,
        mock_read_repository: AsyncMock,
    ) -> None:
        """Test list users with default pagination.

        **Property: Query Handler Pagination Defaults**
        **Validates: Requirements 4.7**
        """
        # Arrange
        query = ListUsersQuery()

        users = [
            {"id": "user-1", "email": "user1@example.com", "is_active": True},
            {"id": "user-2", "email": "user2@example.com", "is_active": True},
        ]
        mock_read_repository.list_all.return_value = users

        # Act
        result = await handler.handle(query)

        # Assert
        assert result.is_ok()
        user_list = result.unwrap()
        assert len(user_list) == 2
        assert user_list[0]["id"] == "user-1"

        # Verify default pagination (page=1, page_size=20)
        mock_read_repository.list_all.assert_called_once_with(
            limit=20,
            offset=0,
            include_inactive=False,
        )

    @pytest.mark.asyncio
    async def test_list_users_with_pagination(
        self,
        handler: ListUsersHandler,
        mock_read_repository: AsyncMock,
    ) -> None:
        """Test list users with custom pagination.

        **Property: Query Handler Custom Pagination**
        **Validates: Requirements 4.8**
        """
        # Arrange
        query = ListUsersQuery(page=3, page_size=10)

        users = [{"id": f"user-{i}", "email": f"user{i}@example.com", "is_active": True} for i in range(10)]
        mock_read_repository.list_all.return_value = users

        # Act
        result = await handler.handle(query)

        # Assert
        assert result.is_ok()

        # Verify pagination calculation: offset = (page - 1) * page_size = (3-1)*10 = 20
        mock_read_repository.list_all.assert_called_once_with(
            limit=10,
            offset=20,
            include_inactive=False,
        )

    @pytest.mark.asyncio
    async def test_list_users_include_inactive(
        self,
        handler: ListUsersHandler,
        mock_read_repository: AsyncMock,
    ) -> None:
        """Test list users including inactive users.

        **Property: Query Handler Include Inactive Filter**
        **Validates: Requirements 4.9**
        """
        # Arrange
        query = ListUsersQuery(include_inactive=True)

        users = [
            {"id": "user-1", "email": "active@example.com", "is_active": True},
            {"id": "user-2", "email": "inactive@example.com", "is_active": False},
        ]
        mock_read_repository.list_all.return_value = users

        # Act
        result = await handler.handle(query)

        # Assert
        assert result.is_ok()
        user_list = result.unwrap()
        assert len(user_list) == 2

        # Verify include_inactive flag
        mock_read_repository.list_all.assert_called_once_with(
            limit=20,
            offset=0,
            include_inactive=True,
        )

    @pytest.mark.asyncio
    async def test_list_users_cache_key(self) -> None:
        """Test query generates correct cache key with params.

        **Property: Cache Key Generation with Parameters**
        **Validates: Requirements 4.10**
        """
        # Arrange
        query = ListUsersQuery(page=2, page_size=50, include_inactive=True)

        # Act
        cache_key = query.get_cache_key()

        # Assert
        assert cache_key == "users:list:2:50:True"

    @pytest.mark.asyncio
    async def test_list_users_empty_result(
        self,
        handler: ListUsersHandler,
        mock_read_repository: AsyncMock,
    ) -> None:
        """Test list users with no results.

        **Property: Query Handler Empty Result**
        **Validates: Requirements 4.11**
        """
        # Arrange
        query = ListUsersQuery()

        mock_read_repository.list_all.return_value = []

        # Act
        result = await handler.handle(query)

        # Assert
        assert result.is_ok()
        user_list = result.unwrap()
        assert len(user_list) == 0
        assert user_list == []
