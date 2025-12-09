"""Unit tests for BaseUseCase in core/base/patterns.

**Feature: test-coverage-90-percent**
"""

from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import BaseModel

from core.base.patterns.use_case import BaseUseCase, IMapper, IRepository
from core.errors.base.domain_errors import EntityNotFoundError


class SampleEntity(BaseModel):
    """Sample entity for testing."""
    id: str
    name: str
    value: int = 0


class SampleCreateDTO(BaseModel):
    """Sample create DTO."""
    name: str
    value: int = 0


class SampleUpdateDTO(BaseModel):
    """Sample update DTO."""
    name: str | None = None
    value: int | None = None


class SampleResponseDTO(BaseModel):
    """Sample response DTO."""
    id: str
    name: str
    value: int


class MockMapper:
    """Mock mapper implementation."""

    def to_dto(self, entity: SampleEntity) -> SampleResponseDTO:
        return SampleResponseDTO(id=entity.id, name=entity.name, value=entity.value)

    def to_dto_list(self, entities: list[SampleEntity]) -> list[SampleResponseDTO]:
        return [self.to_dto(e) for e in entities]


class MockRepository:
    """Mock repository implementation."""

    def __init__(self) -> None:
        self._data: dict[str, SampleEntity] = {}

    async def get_by_id(self, id: str) -> SampleEntity | None:
        return self._data.get(id)

    async def get_all(
        self,
        skip: int,
        limit: int,
        filters: dict | None,
        sort_by: str | None,
        sort_order: str,
    ) -> tuple[list[SampleEntity], int]:
        items = list(self._data.values())[skip:skip + limit]
        return items, len(self._data)

    async def create(self, data: SampleCreateDTO) -> SampleEntity:
        entity = SampleEntity(id=f"id-{len(self._data)}", name=data.name, value=data.value)
        self._data[entity.id] = entity
        return entity

    async def update(self, id: str, data: SampleUpdateDTO) -> SampleEntity | None:
        if id not in self._data:
            return None
        entity = self._data[id]
        if data.name is not None:
            entity.name = data.name
        if data.value is not None:
            entity.value = data.value
        return entity

    async def delete(self, id: str) -> bool:
        if id in self._data:
            del self._data[id]
            return True
        return False

    async def exists(self, id: str) -> bool:
        return id in self._data

    async def create_many(self, data: list[SampleCreateDTO]) -> list[SampleEntity]:
        return [await self.create(d) for d in data]


class MockUnitOfWork:
    """Mock unit of work."""

    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False

    async def __aenter__(self) -> "MockUnitOfWork":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        pass

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


@pytest.fixture
def repository() -> MockRepository:
    """Create mock repository."""
    return MockRepository()


@pytest.fixture
def mapper() -> MockMapper:
    """Create mock mapper."""
    return MockMapper()


@pytest.fixture
def uow() -> MockUnitOfWork:
    """Create mock unit of work."""
    return MockUnitOfWork()


@pytest.fixture
def use_case(
    repository: MockRepository, mapper: MockMapper, uow: MockUnitOfWork
) -> BaseUseCase[SampleEntity, SampleCreateDTO, SampleUpdateDTO, SampleResponseDTO]:
    """Create use case instance."""
    return BaseUseCase(
        repository=repository,
        mapper=mapper,
        entity_name="Sample",
        unit_of_work=uow,
    )


@pytest.fixture
def use_case_no_uow(
    repository: MockRepository, mapper: MockMapper
) -> BaseUseCase[SampleEntity, SampleCreateDTO, SampleUpdateDTO, SampleResponseDTO]:
    """Create use case without unit of work."""
    return BaseUseCase(
        repository=repository,
        mapper=mapper,
        entity_name="Sample",
    )


class TestBaseUseCaseGet:
    """Tests for get method."""

    @pytest.mark.asyncio
    async def test_get_existing_entity(
        self,
        use_case: BaseUseCase,
        repository: MockRepository,
    ) -> None:
        """Test getting existing entity."""
        entity = SampleEntity(id="test-1", name="Test", value=100)
        repository._data["test-1"] = entity

        result = await use_case.get("test-1")

        assert result.id == "test-1"
        assert result.name == "Test"

    @pytest.mark.asyncio
    async def test_get_missing_entity_raises(self, use_case: BaseUseCase) -> None:
        """Test getting missing entity raises error."""
        with pytest.raises(EntityNotFoundError):
            await use_case.get("nonexistent")

    @pytest.mark.asyncio
    async def test_get_missing_entity_returns_none(self, use_case: BaseUseCase) -> None:
        """Test getting missing entity returns None when not raising."""
        result = await use_case.get("nonexistent", raise_on_missing=False)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_or_none(self, use_case: BaseUseCase) -> None:
        """Test get_or_none convenience method."""
        result = await use_case.get_or_none("nonexistent")
        assert result is None


class TestBaseUseCaseList:
    """Tests for list method."""

    @pytest.mark.asyncio
    async def test_list_empty(self, use_case: BaseUseCase) -> None:
        """Test listing empty repository."""
        result = await use_case.list()

        assert result.total == 0
        assert len(result.items) == 0

    @pytest.mark.asyncio
    async def test_list_with_data(
        self, use_case: BaseUseCase, repository: MockRepository
    ) -> None:
        """Test listing with data."""
        repository._data["1"] = SampleEntity(id="1", name="One", value=1)
        repository._data["2"] = SampleEntity(id="2", name="Two", value=2)

        result = await use_case.list(page=1, size=10)

        assert result.total == 2
        assert len(result.items) == 2

    @pytest.mark.asyncio
    async def test_list_pagination(
        self, use_case: BaseUseCase, repository: MockRepository
    ) -> None:
        """Test list pagination."""
        for i in range(5):
            repository._data[str(i)] = SampleEntity(id=str(i), name=f"Item {i}", value=i)

        result = await use_case.list(page=1, size=2)

        assert result.page == 1
        assert result.size == 2


class TestBaseUseCaseCreate:
    """Tests for create method."""

    @pytest.mark.asyncio
    async def test_create_entity(self, use_case: BaseUseCase) -> None:
        """Test creating entity."""
        data = SampleCreateDTO(name="New Item", value=50)

        result = await use_case.create(data)

        assert result.name == "New Item"
        assert result.value == 50


class TestBaseUseCaseUpdate:
    """Tests for update method."""

    @pytest.mark.asyncio
    async def test_update_existing_entity(
        self, use_case: BaseUseCase, repository: MockRepository
    ) -> None:
        """Test updating existing entity."""
        repository._data["test-1"] = SampleEntity(id="test-1", name="Old", value=10)
        data = SampleUpdateDTO(name="Updated", value=99)

        result = await use_case.update("test-1", data)

        assert result.name == "Updated"
        assert result.value == 99

    @pytest.mark.asyncio
    async def test_update_missing_entity_raises(self, use_case: BaseUseCase) -> None:
        """Test updating missing entity raises error."""
        data = SampleUpdateDTO(name="Updated")

        with pytest.raises(EntityNotFoundError):
            await use_case.update("nonexistent", data)


class TestBaseUseCaseDelete:
    """Tests for delete method."""

    @pytest.mark.asyncio
    async def test_delete_existing_entity(
        self, use_case: BaseUseCase, repository: MockRepository
    ) -> None:
        """Test deleting existing entity."""
        repository._data["test-1"] = SampleEntity(id="test-1", name="Test", value=10)

        result = await use_case.delete("test-1")

        assert result is True
        assert "test-1" not in repository._data

    @pytest.mark.asyncio
    async def test_delete_missing_entity_raises(self, use_case: BaseUseCase) -> None:
        """Test deleting missing entity raises error."""
        with pytest.raises(EntityNotFoundError):
            await use_case.delete("nonexistent")


class TestBaseUseCaseExists:
    """Tests for exists method."""

    @pytest.mark.asyncio
    async def test_exists_true(
        self, use_case: BaseUseCase, repository: MockRepository
    ) -> None:
        """Test exists returns True for existing entity."""
        repository._data["test-1"] = SampleEntity(id="test-1", name="Test", value=10)

        result = await use_case.exists("test-1")

        assert result is True

    @pytest.mark.asyncio
    async def test_exists_false(self, use_case: BaseUseCase) -> None:
        """Test exists returns False for missing entity."""
        result = await use_case.exists("nonexistent")
        assert result is False


class TestBaseUseCaseCreateMany:
    """Tests for create_many method."""

    @pytest.mark.asyncio
    async def test_create_many(self, use_case: BaseUseCase) -> None:
        """Test bulk creation."""
        data = [
            SampleCreateDTO(name="Item 1", value=1),
            SampleCreateDTO(name="Item 2", value=2),
        ]

        result = await use_case.create_many(data)

        assert len(result) == 2
        assert result[0].name == "Item 1"
        assert result[1].name == "Item 2"


class TestBaseUseCaseTransaction:
    """Tests for transaction context manager."""

    @pytest.mark.asyncio
    async def test_transaction_commits_on_success(
        self, use_case: BaseUseCase, uow: MockUnitOfWork
    ) -> None:
        """Test transaction commits on success."""
        async with use_case.transaction():
            pass

        assert uow.committed is True

    @pytest.mark.asyncio
    async def test_transaction_rollbacks_on_error(
        self, use_case: BaseUseCase, uow: MockUnitOfWork
    ) -> None:
        """Test transaction rollbacks on error."""
        with pytest.raises(ValueError):
            async with use_case.transaction():
                raise ValueError("Test error")

        assert uow.rolled_back is True

    @pytest.mark.asyncio
    async def test_transaction_without_uow(self, use_case_no_uow: BaseUseCase) -> None:
        """Test transaction works without unit of work."""
        async with use_case_no_uow.transaction():
            pass  # Should not raise
