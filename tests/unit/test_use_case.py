"""Unit tests for BaseUseCase."""

import pytest
from pydantic import BaseModel

from my_app.core.exceptions import EntityNotFoundError
from my_app.application.common.mapper import AutoMapper
from my_app.core.base.repository import InMemoryRepository
from my_app.shared.use_case import BaseUseCase


# Test models
class ItemEntity(BaseModel):
    """Item entity."""

    id: str | None = None
    name: str
    price: float
    is_deleted: bool = False


class ItemCreateDTO(BaseModel):
    """Item create DTO."""

    name: str
    price: float


class ItemUpdateDTO(BaseModel):
    """Item update DTO."""

    name: str | None = None
    price: float | None = None


class ItemResponseDTO(BaseModel):
    """Item response DTO."""

    id: str | None = None
    name: str
    price: float


@pytest.fixture
def repository() -> InMemoryRepository[ItemEntity, ItemCreateDTO, ItemUpdateDTO]:
    """Create repository fixture."""
    return InMemoryRepository(ItemEntity)


@pytest.fixture
def mapper() -> AutoMapper[ItemEntity, ItemResponseDTO]:
    """Create mapper fixture."""
    return AutoMapper(ItemEntity, ItemResponseDTO)


@pytest.fixture
def use_case(
    repository: InMemoryRepository[ItemEntity, ItemCreateDTO, ItemUpdateDTO],
    mapper: AutoMapper[ItemEntity, ItemResponseDTO],
) -> BaseUseCase[ItemEntity, ItemCreateDTO, ItemUpdateDTO, ItemResponseDTO]:
    """Create use case fixture."""
    return BaseUseCase(repository, mapper, entity_name="Item")


class TestUseCaseCreate:
    """Tests for use case create operation."""

    @pytest.mark.asyncio
    async def test_create_returns_response_dto(
        self, use_case: BaseUseCase[ItemEntity, ItemCreateDTO, ItemUpdateDTO, ItemResponseDTO]
    ) -> None:
        """Create SHALL return a response DTO with generated ID."""
        create_data = ItemCreateDTO(name="Test Item", price=99.99)

        result = await use_case.create(create_data)

        assert result.id is not None
        assert result.name == "Test Item"
        assert result.price == 99.99


class TestUseCaseGet:
    """Tests for use case get operation."""

    @pytest.mark.asyncio
    async def test_get_existing_entity(
        self, use_case: BaseUseCase[ItemEntity, ItemCreateDTO, ItemUpdateDTO, ItemResponseDTO]
    ) -> None:
        """Get SHALL return entity when it exists."""
        created = await use_case.create(ItemCreateDTO(name="Test", price=10.0))

        result = await use_case.get(created.id)

        assert result.id == created.id
        assert result.name == "Test"

    @pytest.mark.asyncio
    async def test_get_nonexistent_raises_error(
        self, use_case: BaseUseCase[ItemEntity, ItemCreateDTO, ItemUpdateDTO, ItemResponseDTO]
    ) -> None:
        """Get SHALL raise EntityNotFoundError when entity doesn't exist."""
        with pytest.raises(EntityNotFoundError) as exc_info:
            await use_case.get("nonexistent")

        assert exc_info.value.status_code == 404
        assert "Item" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_get_or_none_returns_none(
        self, use_case: BaseUseCase[ItemEntity, ItemCreateDTO, ItemUpdateDTO, ItemResponseDTO]
    ) -> None:
        """get_or_none SHALL return None when entity doesn't exist."""
        result = await use_case.get_or_none("nonexistent")
        assert result is None


class TestUseCaseUpdate:
    """Tests for use case update operation."""

    @pytest.mark.asyncio
    async def test_update_existing_entity(
        self, use_case: BaseUseCase[ItemEntity, ItemCreateDTO, ItemUpdateDTO, ItemResponseDTO]
    ) -> None:
        """Update SHALL modify and return updated entity."""
        created = await use_case.create(ItemCreateDTO(name="Original", price=10.0))

        result = await use_case.update(created.id, ItemUpdateDTO(name="Updated", price=20.0))

        assert result.name == "Updated"
        assert result.price == 20.0

    @pytest.mark.asyncio
    async def test_update_nonexistent_raises_error(
        self, use_case: BaseUseCase[ItemEntity, ItemCreateDTO, ItemUpdateDTO, ItemResponseDTO]
    ) -> None:
        """Update SHALL raise EntityNotFoundError when entity doesn't exist."""
        with pytest.raises(EntityNotFoundError):
            await use_case.update("nonexistent", ItemUpdateDTO(name="Test"))


class TestUseCaseDelete:
    """Tests for use case delete operation."""

    @pytest.mark.asyncio
    async def test_delete_existing_entity(
        self, use_case: BaseUseCase[ItemEntity, ItemCreateDTO, ItemUpdateDTO, ItemResponseDTO]
    ) -> None:
        """Delete SHALL return True and remove entity."""
        created = await use_case.create(ItemCreateDTO(name="Test", price=10.0))

        result = await use_case.delete(created.id)

        assert result is True
        assert await use_case.exists(created.id) is False

    @pytest.mark.asyncio
    async def test_delete_nonexistent_raises_error(
        self, use_case: BaseUseCase[ItemEntity, ItemCreateDTO, ItemUpdateDTO, ItemResponseDTO]
    ) -> None:
        """Delete SHALL raise EntityNotFoundError when entity doesn't exist."""
        with pytest.raises(EntityNotFoundError):
            await use_case.delete("nonexistent")


class TestUseCaseList:
    """Tests for use case list operation."""

    @pytest.mark.asyncio
    async def test_list_returns_paginated_response(
        self, use_case: BaseUseCase[ItemEntity, ItemCreateDTO, ItemUpdateDTO, ItemResponseDTO]
    ) -> None:
        """List SHALL return PaginatedResponse with items."""
        await use_case.create(ItemCreateDTO(name="Item 1", price=10.0))
        await use_case.create(ItemCreateDTO(name="Item 2", price=20.0))

        result = await use_case.list(page=1, size=10)

        assert result.total == 2
        assert len(result.items) == 2
        assert result.page == 1
        assert result.size == 10

    @pytest.mark.asyncio
    async def test_list_pagination(
        self, use_case: BaseUseCase[ItemEntity, ItemCreateDTO, ItemUpdateDTO, ItemResponseDTO]
    ) -> None:
        """List SHALL respect pagination parameters."""
        for i in range(5):
            await use_case.create(ItemCreateDTO(name=f"Item {i}", price=float(i)))

        result = await use_case.list(page=2, size=2)

        assert result.total == 5
        assert len(result.items) == 2
        assert result.page == 2
        assert result.has_previous is True
        assert result.has_next is True
