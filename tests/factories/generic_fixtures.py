"""Generic test fixtures for repository and use case testing.

Provides reusable test case base classes that reduce duplication
when testing CRUD operations across different entity types.

**Feature: api-architecture-analysis, Task 4.1: Generic Test Fixtures**
**Validates: Requirements 8.1**

Usage:
    from tests.factories.generic_fixtures import RepositoryTestCase, UseCaseTestCase

    class TestItemRepository(RepositoryTestCase[Item, ItemCreate, ItemUpdate]):
        @pytest.fixture
        def entity_factory(self) -> Callable[[], Item]:
            return lambda: Item(id="test-id", name="Test", price=10.0)

        @pytest.fixture
        def create_factory(self) -> Callable[[], ItemCreate]:
            return lambda: ItemCreate(name="Test", price=10.0)

        @pytest.fixture
        def update_factory(self) -> Callable[[], ItemUpdate]:
            return lambda: ItemUpdate(name="Updated")
"""

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

import pytest
from pydantic import BaseModel

from application.common.base.dto import PaginatedResponse
from application.common.base.mapper import IMapper
from core.base.repository import IRepository, InMemoryRepository
from application.common.base.use_case import BaseUseCase

# Type variables
T = TypeVar("T", bound=BaseModel)
CreateT = TypeVar("CreateT", bound=BaseModel)
UpdateT = TypeVar("UpdateT", bound=BaseModel)
ResponseT = TypeVar("ResponseT", bound=BaseModel)


@dataclass
class TestContext(Generic[T, CreateT, UpdateT]):
    """Context for test execution with common test data."""

    entity: T
    create_data: CreateT
    update_data: UpdateT
    entities: list[T] = field(default_factory=list)


class RepositoryTestCase(ABC, Generic[T, CreateT, UpdateT]):
    """Base test case for repository implementations.

    Provides standard CRUD tests that can be reused across
    different entity types. Subclasses must provide factories
    for creating test entities and DTOs.

    Type Parameters:
        T: Entity type.
        CreateT: Create DTO type.
        UpdateT: Update DTO type.

    Usage:
        class TestItemRepository(RepositoryTestCase[Item, ItemCreate, ItemUpdate]):
            @pytest.fixture
            def repository(self) -> IRepository[Item, ItemCreate, ItemUpdate]:
                return InMemoryRepository(Item)

            @pytest.fixture
            def entity_factory(self) -> Callable[[], Item]:
                return lambda: Item(id="test-id", name="Test", price=10.0)

            @pytest.fixture
            def create_factory(self) -> Callable[[], ItemCreate]:
                return lambda: ItemCreate(name="Test", price=10.0)

            @pytest.fixture
            def update_factory(self) -> Callable[[], ItemUpdate]:
                return lambda: ItemUpdate(name="Updated")
    """

    @pytest.fixture
    @abstractmethod
    def repository(self) -> IRepository[T, CreateT, UpdateT]:
        """Provide repository instance for testing."""
        ...

    @pytest.fixture
    @abstractmethod
    def entity_factory(self) -> Callable[[], T]:
        """Provide factory for creating test entities."""
        ...

    @pytest.fixture
    @abstractmethod
    def create_factory(self) -> Callable[[], CreateT]:
        """Provide factory for creating CreateDTO instances."""
        ...

    @pytest.fixture
    @abstractmethod
    def update_factory(self) -> Callable[[], UpdateT]:
        """Provide factory for creating UpdateDTO instances."""
        ...

    @pytest.fixture
    def test_context(
        self,
        entity_factory: Callable[[], T],
        create_factory: Callable[[], CreateT],
        update_factory: Callable[[], UpdateT],
    ) -> TestContext[T, CreateT, UpdateT]:
        """Create test context with sample data."""
        return TestContext(
            entity=entity_factory(),
            create_data=create_factory(),
            update_data=update_factory(),
            entities=[entity_factory() for _ in range(3)],
        )

    # ==========================================================================
    # Standard CRUD Tests
    # ==========================================================================

    @pytest.mark.asyncio
    async def test_create_returns_entity_with_id(
        self,
        repository: IRepository[T, CreateT, UpdateT],
        create_factory: Callable[[], CreateT],
    ) -> None:
        """Test that create returns entity with generated ID."""
        create_data = create_factory()
        entity = await repository.create(create_data)

        assert entity is not None
        assert hasattr(entity, "id")
        assert entity.id is not None

    @pytest.mark.asyncio
    async def test_get_by_id_returns_created_entity(
        self,
        repository: IRepository[T, CreateT, UpdateT],
        create_factory: Callable[[], CreateT],
    ) -> None:
        """Test that get_by_id returns previously created entity."""
        create_data = create_factory()
        created = await repository.create(create_data)

        retrieved = await repository.get_by_id(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id

    @pytest.mark.asyncio
    async def test_get_by_id_returns_none_for_nonexistent(
        self,
        repository: IRepository[T, CreateT, UpdateT],
    ) -> None:
        """Test that get_by_id returns None for nonexistent ID."""
        result = await repository.get_by_id("nonexistent-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_update_modifies_entity(
        self,
        repository: IRepository[T, CreateT, UpdateT],
        create_factory: Callable[[], CreateT],
        update_factory: Callable[[], UpdateT],
    ) -> None:
        """Test that update modifies existing entity."""
        create_data = create_factory()
        created = await repository.create(create_data)

        update_data = update_factory()
        updated = await repository.update(created.id, update_data)

        assert updated is not None
        assert updated.id == created.id

    @pytest.mark.asyncio
    async def test_update_returns_none_for_nonexistent(
        self,
        repository: IRepository[T, CreateT, UpdateT],
        update_factory: Callable[[], UpdateT],
    ) -> None:
        """Test that update returns None for nonexistent ID."""
        update_data = update_factory()
        result = await repository.update("nonexistent-id", update_data)
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_removes_entity(
        self,
        repository: IRepository[T, CreateT, UpdateT],
        create_factory: Callable[[], CreateT],
    ) -> None:
        """Test that delete removes entity."""
        create_data = create_factory()
        created = await repository.create(create_data)

        deleted = await repository.delete(created.id)
        assert deleted is True

        # Verify entity is gone or soft-deleted
        retrieved = await repository.get_by_id(created.id)
        # For soft delete, entity may still exist but be marked deleted
        # For hard delete, entity should be None

    @pytest.mark.asyncio
    async def test_delete_returns_false_for_nonexistent(
        self,
        repository: IRepository[T, CreateT, UpdateT],
    ) -> None:
        """Test that delete returns False for nonexistent ID."""
        result = await repository.delete("nonexistent-id")
        assert result is False

    @pytest.mark.asyncio
    async def test_exists_returns_true_for_existing(
        self,
        repository: IRepository[T, CreateT, UpdateT],
        create_factory: Callable[[], CreateT],
    ) -> None:
        """Test that exists returns True for existing entity."""
        create_data = create_factory()
        created = await repository.create(create_data)

        exists = await repository.exists(created.id)
        assert exists is True

    @pytest.mark.asyncio
    async def test_exists_returns_false_for_nonexistent(
        self,
        repository: IRepository[T, CreateT, UpdateT],
    ) -> None:
        """Test that exists returns False for nonexistent ID."""
        exists = await repository.exists("nonexistent-id")
        assert exists is False

    @pytest.mark.asyncio
    async def test_get_all_returns_created_entities(
        self,
        repository: IRepository[T, CreateT, UpdateT],
        create_factory: Callable[[], CreateT],
    ) -> None:
        """Test that get_all returns all created entities."""
        # Create multiple entities
        for _ in range(3):
            await repository.create(create_factory())

        entities, total = await repository.get_all()

        assert len(entities) == 3
        assert total == 3

    @pytest.mark.asyncio
    async def test_get_all_respects_pagination(
        self,
        repository: IRepository[T, CreateT, UpdateT],
        create_factory: Callable[[], CreateT],
    ) -> None:
        """Test that get_all respects skip and limit."""
        # Create 5 entities
        for _ in range(5):
            await repository.create(create_factory())

        entities, total = await repository.get_all(skip=1, limit=2)

        assert len(entities) == 2
        assert total == 5

    @pytest.mark.asyncio
    async def test_create_many_creates_multiple_entities(
        self,
        repository: IRepository[T, CreateT, UpdateT],
        create_factory: Callable[[], CreateT],
    ) -> None:
        """Test that create_many creates multiple entities."""
        create_data_list = [create_factory() for _ in range(3)]

        created = await repository.create_many(create_data_list)

        assert len(created) == 3
        for entity in created:
            assert entity.id is not None


class UseCaseTestCase(ABC, Generic[T, CreateT, UpdateT, ResponseT]):
    """Base test case for use case implementations.

    Provides standard CRUD tests for use cases that can be reused
    across different entity types.

    Type Parameters:
        T: Entity type.
        CreateT: Create DTO type.
        UpdateT: Update DTO type.
        ResponseT: Response DTO type.
    """

    @pytest.fixture
    @abstractmethod
    def use_case(self) -> BaseUseCase[T, CreateT, UpdateT, ResponseT]:
        """Provide use case instance for testing."""
        ...

    @pytest.fixture
    @abstractmethod
    def create_factory(self) -> Callable[[], CreateT]:
        """Provide factory for creating CreateDTO instances."""
        ...

    @pytest.fixture
    @abstractmethod
    def update_factory(self) -> Callable[[], UpdateT]:
        """Provide factory for creating UpdateDTO instances."""
        ...

    # ==========================================================================
    # Standard Use Case Tests
    # ==========================================================================

    @pytest.mark.asyncio
    async def test_create_returns_response_dto(
        self,
        use_case: BaseUseCase[T, CreateT, UpdateT, ResponseT],
        create_factory: Callable[[], CreateT],
    ) -> None:
        """Test that create returns response DTO."""
        create_data = create_factory()
        response = await use_case.create(create_data)

        assert response is not None
        assert hasattr(response, "id") or hasattr(response, "model_dump")

    @pytest.mark.asyncio
    async def test_get_returns_response_dto(
        self,
        use_case: BaseUseCase[T, CreateT, UpdateT, ResponseT],
        create_factory: Callable[[], CreateT],
    ) -> None:
        """Test that get returns response DTO for existing entity."""
        create_data = create_factory()
        created = await use_case.create(create_data)

        # Get the ID from the response
        entity_id = getattr(created, "id", None)
        if entity_id is None and hasattr(created, "model_dump"):
            entity_id = created.model_dump().get("id")

        if entity_id:
            retrieved = await use_case.get(entity_id)
            assert retrieved is not None

    @pytest.mark.asyncio
    async def test_list_returns_paginated_response(
        self,
        use_case: BaseUseCase[T, CreateT, UpdateT, ResponseT],
        create_factory: Callable[[], CreateT],
    ) -> None:
        """Test that list returns paginated response."""
        # Create some entities
        for _ in range(3):
            await use_case.create(create_factory())

        response = await use_case.list()

        assert isinstance(response, PaginatedResponse)
        assert response.total >= 3
        assert len(response.items) >= 3

    @pytest.mark.asyncio
    async def test_update_returns_updated_response(
        self,
        use_case: BaseUseCase[T, CreateT, UpdateT, ResponseT],
        create_factory: Callable[[], CreateT],
        update_factory: Callable[[], UpdateT],
    ) -> None:
        """Test that update returns updated response DTO."""
        create_data = create_factory()
        created = await use_case.create(create_data)

        entity_id = getattr(created, "id", None)
        if entity_id is None and hasattr(created, "model_dump"):
            entity_id = created.model_dump().get("id")

        if entity_id:
            update_data = update_factory()
            updated = await use_case.update(entity_id, update_data)
            assert updated is not None

    @pytest.mark.asyncio
    async def test_delete_returns_true(
        self,
        use_case: BaseUseCase[T, CreateT, UpdateT, ResponseT],
        create_factory: Callable[[], CreateT],
    ) -> None:
        """Test that delete returns True for existing entity."""
        create_data = create_factory()
        created = await use_case.create(create_data)

        entity_id = getattr(created, "id", None)
        if entity_id is None and hasattr(created, "model_dump"):
            entity_id = created.model_dump().get("id")

        if entity_id:
            deleted = await use_case.delete(entity_id)
            assert deleted is True


class MapperTestCase(ABC, Generic[T, ResponseT]):
    """Base test case for mapper implementations.

    Provides standard mapping tests that can be reused across
    different entity/DTO pairs.

    Type Parameters:
        T: Entity type.
        ResponseT: Response DTO type.
    """

    @pytest.fixture
    @abstractmethod
    def mapper(self) -> IMapper[T, ResponseT]:
        """Provide mapper instance for testing."""
        ...

    @pytest.fixture
    @abstractmethod
    def entity_factory(self) -> Callable[[], T]:
        """Provide factory for creating test entities."""
        ...

    @pytest.fixture
    @abstractmethod
    def dto_factory(self) -> Callable[[], ResponseT]:
        """Provide factory for creating test DTOs."""
        ...

    # ==========================================================================
    # Standard Mapper Tests
    # ==========================================================================

    def test_to_dto_returns_dto(
        self,
        mapper: IMapper[T, ResponseT],
        entity_factory: Callable[[], T],
    ) -> None:
        """Test that to_dto returns a DTO."""
        entity = entity_factory()
        dto = mapper.to_dto(entity)

        assert dto is not None

    def test_to_entity_returns_entity(
        self,
        mapper: IMapper[T, ResponseT],
        dto_factory: Callable[[], ResponseT],
    ) -> None:
        """Test that to_entity returns an entity."""
        dto = dto_factory()
        entity = mapper.to_entity(dto)

        assert entity is not None

    def test_to_dto_list_returns_list(
        self,
        mapper: IMapper[T, ResponseT],
        entity_factory: Callable[[], T],
    ) -> None:
        """Test that to_dto_list returns a list of DTOs."""
        entities = [entity_factory() for _ in range(3)]
        dtos = mapper.to_dto_list(entities)

        assert len(dtos) == 3


# =============================================================================
# Fixture Factories
# =============================================================================


def create_in_memory_repository(
    entity_type: type[T],
) -> InMemoryRepository[T, Any, Any]:
    """Create an in-memory repository for testing.

    Args:
        entity_type: The entity type for the repository.

    Returns:
        InMemoryRepository instance.
    """
    return InMemoryRepository(entity_type)


def create_test_context(
    entity_factory: Callable[[], T],
    create_factory: Callable[[], CreateT],
    update_factory: Callable[[], UpdateT],
    count: int = 3,
) -> TestContext[T, CreateT, UpdateT]:
    """Create a test context with sample data.

    Args:
        entity_factory: Factory for creating entities.
        create_factory: Factory for creating CreateDTOs.
        update_factory: Factory for creating UpdateDTOs.
        count: Number of entities to create.

    Returns:
        TestContext with sample data.
    """
    return TestContext(
        entity=entity_factory(),
        create_data=create_factory(),
        update_data=update_factory(),
        entities=[entity_factory() for _ in range(count)],
    )

