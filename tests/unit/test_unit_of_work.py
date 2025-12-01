"""Unit tests for Unit of Work pattern."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from my_app.shared.unit_of_work import (
    IUnitOfWork,
    SQLAlchemyUnitOfWork,
    transaction,
)


class TestSQLAlchemyUnitOfWork:
    """Tests for SQLAlchemyUnitOfWork."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create mock async session."""
        session = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.close = AsyncMock()
        return session

    @pytest.fixture
    def uow(self, mock_session: AsyncMock) -> SQLAlchemyUnitOfWork:
        """Create UoW with mock session."""
        return SQLAlchemyUnitOfWork(mock_session)

    @pytest.mark.asyncio
    async def test_commit_calls_session_commit(
        self, uow: SQLAlchemyUnitOfWork, mock_session: AsyncMock
    ) -> None:
        """Test that commit delegates to session."""
        await uow.commit()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_rollback_calls_session_rollback(
        self, uow: SQLAlchemyUnitOfWork, mock_session: AsyncMock
    ) -> None:
        """Test that rollback delegates to session."""
        await uow.rollback()
        mock_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager_closes_session(
        self, uow: SQLAlchemyUnitOfWork, mock_session: AsyncMock
    ) -> None:
        """Test that context manager closes session on exit."""
        async with uow:
            pass
        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager_rollback_on_error(
        self, uow: SQLAlchemyUnitOfWork, mock_session: AsyncMock
    ) -> None:
        """Test that context manager rolls back on exception."""
        with pytest.raises(ValueError):
            async with uow:
                raise ValueError("Test error")

        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager_no_rollback_on_success(
        self, uow: SQLAlchemyUnitOfWork, mock_session: AsyncMock
    ) -> None:
        """Test that context manager doesn't rollback on success."""
        async with uow:
            pass

        mock_session.rollback.assert_not_called()
        mock_session.close.assert_called_once()

    def test_session_property(
        self, uow: SQLAlchemyUnitOfWork, mock_session: AsyncMock
    ) -> None:
        """Test session property returns underlying session."""
        assert uow.session is mock_session


class TestTransactionContextManager:
    """Tests for transaction context manager."""

    @pytest.fixture
    def mock_uow(self) -> AsyncMock:
        """Create mock UoW."""
        uow = AsyncMock(spec=IUnitOfWork)
        uow.commit = AsyncMock()
        uow.rollback = AsyncMock()
        return uow

    @pytest.mark.asyncio
    async def test_transaction_commits_on_success(
        self, mock_uow: AsyncMock
    ) -> None:
        """Test that transaction commits on successful completion."""
        async with transaction(mock_uow):
            pass

        mock_uow.commit.assert_called_once()
        mock_uow.rollback.assert_not_called()

    @pytest.mark.asyncio
    async def test_transaction_rollback_on_error(
        self, mock_uow: AsyncMock
    ) -> None:
        """Test that transaction rolls back on exception."""
        with pytest.raises(ValueError):
            async with transaction(mock_uow):
                raise ValueError("Test error")

        mock_uow.rollback.assert_called_once()
        mock_uow.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_transaction_yields_uow(
        self, mock_uow: AsyncMock
    ) -> None:
        """Test that transaction yields the UoW instance."""
        async with transaction(mock_uow) as yielded:
            assert yielded is mock_uow

    @pytest.mark.asyncio
    async def test_transaction_reraises_exception(
        self, mock_uow: AsyncMock
    ) -> None:
        """Test that transaction re-raises the original exception."""
        class CustomError(Exception):
            pass

        with pytest.raises(CustomError):
            async with transaction(mock_uow):
                raise CustomError("Custom error")
