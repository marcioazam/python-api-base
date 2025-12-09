"""Unit tests for GenericService.

**Feature: python-api-base-2025-validation**
**Validates: Requirements 22.1, 22.2, 22.3, 22.4**
"""

from collections.abc import Sequence
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import BaseModel

from application.common.services import (
    GenericService,
    NotFoundError,
    ServiceError,
    ValidationError,
)
from core.base.patterns.result import Err, Ok, Result


# Test DTOs
class TestEntity(BaseModel):
    """Test entity."""

    id: str
    name: str
    value: int = 0


class TestCreate(BaseModel):
    """Test create DTO."""

    name: str
    value: int = 0


class TestUpdate(BaseModel):
    """Test update DTO."""

    name: str | None = None
    value: int | None = None


class TestResponse(BaseModel):
    """Test response DTO."""

    id: str
    name: str
    value: int


# Test Service Implementation
class TestService(GenericService[TestEntity, TestCreate, TestUpdate, TestResponse]):
    """Test service implementation."""

    entity_name = "TestEntity"


class TestServiceWithValidation(
    GenericService[TestEntity, TestCreate, TestUpdate, TestResponse]
):
    """Test service with custom validation."""

    entity_name = "TestEntity"

    async def _pre_create(self, data: TestCreate) -> Result[TestCreate, ServiceError]:
        if data.value < 0:
            return Err(ValidationError("Value must be non-negative", "value"))
        return Ok(data)

    async def _pre_update(
        self, entity_id: Any, data: TestUpdate, existing: TestEntity
    ) -> Result[TestUpdate, ServiceError]:
        if data.value is not None and data.value < 0:
            return Err(ValidationError("Value must be non-negative", "value"))
        return Ok(data)


@pytest.fixture
def mock_repository() -> AsyncMock:
    """Create mock repository."""
    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=None)
    repo.get_all = AsyncMock(return_value=([], 0))
    repo.create = AsyncMock()
    repo.update = AsyncMock()
    repo.delete = AsyncMock(return_value=True)
    repo.create_many = AsyncMock(return_value=[])
    repo.exists = AsyncMock(return_value=False)
    return repo


@pytest.fixture
def mock_mapper() -> MagicMock:
    """Create mock mapper."""
    mapper = MagicMock()
    mapper.to_dto = MagicMock(
        side_effect=lambda e: TestResponse(id=e.id, name=e.name, value=e.value)
    )
    return mapper


@pytest.fixture
def service(mock_repository: AsyncMock, mock_mapper: MagicMock) -> TestService:
    """Create test service."""
    return TestService(mock_repository, mock_mapper)


@pytest.fixture
def service_with_validation(
    mock_repository: AsyncMock, mock_mapper: MagicMock
) -> TestServiceWithValidation:
    """Create test service with validation."""
    return TestServiceWithValidation(mock_repository, mock_mapper)


class TestGenericServiceCreate:
    """Tests for create operations."""

    @pytest.mark.asyncio
    async def test_create_success(
        self, service: TestService, mock_repository: AsyncMock
    ) -> None:
        """Create should return response on success."""
        entity = TestEntity(id="1", name="Test", value=10)
        mock_repository.create.return_value = entity

        result = await service.create(TestCreate(name="Test", value=10))

        assert result.id == "1"
        assert result.name == "Test"
        mock_repository.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_with_result_success(
        self, service: TestService, mock_repository: AsyncMock
    ) -> None:
        """create_with_result should return Ok on success."""
        entity = TestEntity(id="1", name="Test", value=10)
        mock_repository.create.return_value = entity

        result = await service.create_with_result(TestCreate(name="Test", value=10))

        assert result.is_ok()
        assert result.unwrap().id == "1"

    @pytest.mark.asyncio
    async def test_create_validation_failure(
        self,
        service_with_validation: TestServiceWithValidation,
        mock_repository: AsyncMock,
    ) -> None:
        """Create should raise ValidationError on validation failure."""
        with pytest.raises(ValidationError) as exc_info:
            await service_with_validation.create(TestCreate(name="Test", value=-1))

        assert exc_info.value.field == "value"
        mock_repository.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_repository_error(
        self, service: TestService, mock_repository: AsyncMock
    ) -> None:
        """Create should raise ServiceError on repository failure."""
        mock_repository.create.side_effect = Exception("DB error")

        with pytest.raises(ServiceError):
            await service.create(TestCreate(name="Test"))


class TestGenericServiceGet:
    """Tests for get operations."""

    @pytest.mark.asyncio
    async def test_get_success(
        self, service: TestService, mock_repository: AsyncMock
    ) -> None:
        """Get should return response when entity exists."""
        entity = TestEntity(id="1", name="Test", value=10)
        mock_repository.get_by_id.return_value = entity

        result = await service.get("1")

        assert result.id == "1"
        assert result.name == "Test"

    @pytest.mark.asyncio
    async def test_get_not_found(
        self, service: TestService, mock_repository: AsyncMock
    ) -> None:
        """Get should raise NotFoundError when entity doesn't exist."""
        mock_repository.get_by_id.return_value = None

        with pytest.raises(NotFoundError) as exc_info:
            await service.get("nonexistent")

        assert exc_info.value.entity_id == "nonexistent"
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_get_by_id_returns_none(
        self, service: TestService, mock_repository: AsyncMock
    ) -> None:
        """get_by_id should return Ok(None) when entity doesn't exist."""
        mock_repository.get_by_id.return_value = None

        result = await service.get_by_id("nonexistent")

        assert result.is_ok()
        assert result.unwrap() is None


class TestGenericServiceUpdate:
    """Tests for update operations."""

    @pytest.mark.asyncio
    async def test_update_success(
        self, service: TestService, mock_repository: AsyncMock
    ) -> None:
        """Update should return response on success."""
        existing = TestEntity(id="1", name="Old", value=5)
        updated = TestEntity(id="1", name="New", value=10)
        mock_repository.get_by_id.return_value = existing
        mock_repository.update.return_value = updated

        result = await service.update("1", TestUpdate(name="New", value=10))

        assert result.name == "New"
        assert result.value == 10

    @pytest.mark.asyncio
    async def test_update_not_found(
        self, service: TestService, mock_repository: AsyncMock
    ) -> None:
        """Update should raise NotFoundError when entity doesn't exist."""
        mock_repository.get_by_id.return_value = None

        with pytest.raises(NotFoundError):
            await service.update("nonexistent", TestUpdate(name="New"))

    @pytest.mark.asyncio
    async def test_update_validation_failure(
        self,
        service_with_validation: TestServiceWithValidation,
        mock_repository: AsyncMock,
    ) -> None:
        """Update should raise ValidationError on validation failure."""
        existing = TestEntity(id="1", name="Test", value=5)
        mock_repository.get_by_id.return_value = existing

        with pytest.raises(ValidationError):
            await service_with_validation.update("1", TestUpdate(value=-1))


class TestGenericServiceDelete:
    """Tests for delete operations."""

    @pytest.mark.asyncio
    async def test_delete_success(
        self, service: TestService, mock_repository: AsyncMock
    ) -> None:
        """Delete should return True on success."""
        existing = TestEntity(id="1", name="Test", value=5)
        mock_repository.get_by_id.return_value = existing
        mock_repository.delete.return_value = True

        result = await service.delete("1")

        assert result is True
        mock_repository.delete.assert_called_once_with("1", soft=True)

    @pytest.mark.asyncio
    async def test_delete_hard(
        self, service: TestService, mock_repository: AsyncMock
    ) -> None:
        """Delete with soft=False should perform hard delete."""
        existing = TestEntity(id="1", name="Test", value=5)
        mock_repository.get_by_id.return_value = existing
        mock_repository.delete.return_value = True

        result = await service.delete("1", soft=False)

        assert result is True
        mock_repository.delete.assert_called_once_with("1", soft=False)

    @pytest.mark.asyncio
    async def test_delete_not_found(
        self, service: TestService, mock_repository: AsyncMock
    ) -> None:
        """Delete should raise NotFoundError when entity doesn't exist."""
        mock_repository.get_by_id.return_value = None

        with pytest.raises(NotFoundError):
            await service.delete("nonexistent")


class TestGenericServiceList:
    """Tests for list operations."""

    @pytest.mark.asyncio
    async def test_list_success(
        self, service: TestService, mock_repository: AsyncMock
    ) -> None:
        """List should return paginated results."""
        entities = [
            TestEntity(id="1", name="Test1", value=1),
            TestEntity(id="2", name="Test2", value=2),
        ]
        mock_repository.get_all.return_value = (entities, 2)

        items, total = await service.list(page=1, size=10)

        assert len(items) == 2
        assert total == 2
        mock_repository.get_all.assert_called_once_with(
            skip=0, limit=10, filters=None, sort_by=None, sort_order="asc"
        )

    @pytest.mark.asyncio
    async def test_list_pagination(
        self, service: TestService, mock_repository: AsyncMock
    ) -> None:
        """List should calculate correct skip value."""
        mock_repository.get_all.return_value = ([], 0)

        await service.list(page=3, size=20)

        mock_repository.get_all.assert_called_once_with(
            skip=40, limit=20, filters=None, sort_by=None, sort_order="asc"
        )


class TestGenericServiceBulk:
    """Tests for bulk operations."""

    @pytest.mark.asyncio
    async def test_create_many_success(
        self, service: TestService, mock_repository: AsyncMock
    ) -> None:
        """create_many should return list of responses."""
        entities = [
            TestEntity(id="1", name="Test1", value=1),
            TestEntity(id="2", name="Test2", value=2),
        ]
        mock_repository.create_many.return_value = entities

        data = [TestCreate(name="Test1", value=1), TestCreate(name="Test2", value=2)]
        results = await service.create_many(data)

        assert len(results) == 2
        assert results[0].id == "1"
        assert results[1].id == "2"


class TestGenericServiceExists:
    """Tests for exists operation."""

    @pytest.mark.asyncio
    async def test_exists_true(
        self, service: TestService, mock_repository: AsyncMock
    ) -> None:
        """exists should return True when entity exists."""
        mock_repository.exists.return_value = True

        result = await service.exists("1")

        assert result is True

    @pytest.mark.asyncio
    async def test_exists_false(
        self, service: TestService, mock_repository: AsyncMock
    ) -> None:
        """exists should return False when entity doesn't exist."""
        mock_repository.exists.return_value = False

        result = await service.exists("nonexistent")

        assert result is False
