"""Property-based tests for repository interface.

**Feature: generic-fastapi-crud, Property 6-10: Repository Properties**
**Validates: Requirements 3.2, 3.3, 3.4, 3.5, 3.6, 3.7**
"""

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from pydantic import BaseModel

from my_app.core.base.repository import InMemoryRepository


# Test models (prefixed with Sample to avoid pytest collection)
class SampleEntity(BaseModel):
    """Sample entity with soft delete support."""

    id: str | None = None
    name: str
    value: float
    is_deleted: bool = False


class SampleCreateDTO(BaseModel):
    """DTO for creating sample entities."""

    name: str
    value: float


class SampleUpdateDTO(BaseModel):
    """DTO for updating sample entities."""

    name: str | None = None
    value: float | None = None


# Strategies
create_dto_strategy = st.builds(
    SampleCreateDTO,
    name=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("L", "N"))),
    value=st.floats(min_value=0, max_value=10000, allow_nan=False, allow_infinity=False),
)


class TestRepositoryCreateGetRoundTrip:
    """Property tests for repository create-get round-trip."""

    @settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow])
    @given(create_data=create_dto_strategy)
    @pytest.mark.asyncio
    async def test_create_get_round_trip(self, create_data: SampleCreateDTO) -> None:
        """
        **Feature: generic-fastapi-crud, Property 6: Repository Create-Get Round-Trip**
        """
        repo = InMemoryRepository[SampleEntity, SampleCreateDTO, SampleUpdateDTO](SampleEntity)

        created = await repo.create(create_data)
        assert created.id is not None

        retrieved = await repo.get_by_id(created.id)
        assert retrieved is not None
        assert retrieved.name == create_data.name
        assert retrieved.value == create_data.value

    @settings(max_examples=20, suppress_health_check=[HealthCheck.too_slow])
    @given(create_data=create_dto_strategy)
    @pytest.mark.asyncio
    async def test_created_entity_exists(self, create_data: SampleCreateDTO) -> None:
        """After create(), exists() SHALL return True."""
        repo = InMemoryRepository[SampleEntity, SampleCreateDTO, SampleUpdateDTO](SampleEntity)

        created = await repo.create(create_data)
        exists = await repo.exists(created.id)
        assert exists is True


class TestRepositoryUpdatePersistence:
    """Property tests for repository update persistence."""

    @settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow])
    @given(
        create_data=create_dto_strategy,
        new_name=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("L", "N"))),
        new_value=st.floats(min_value=0, max_value=10000, allow_nan=False, allow_infinity=False),
    )
    @pytest.mark.asyncio
    async def test_update_persistence(
        self, create_data: SampleCreateDTO, new_name: str, new_value: float
    ) -> None:
        """
        **Feature: generic-fastapi-crud, Property 7: Repository Update Persistence**
        """
        repo = InMemoryRepository[SampleEntity, SampleCreateDTO, SampleUpdateDTO](SampleEntity)

        created = await repo.create(create_data)
        update_data = SampleUpdateDTO(name=new_name, value=new_value)
        updated = await repo.update(created.id, update_data)

        assert updated is not None
        assert updated.name == new_name
        assert updated.value == new_value

    @pytest.mark.asyncio
    async def test_update_nonexistent_returns_none(self) -> None:
        """Update on non-existent entity SHALL return None."""
        repo = InMemoryRepository[SampleEntity, SampleCreateDTO, SampleUpdateDTO](SampleEntity)
        result = await repo.update("nonexistent", SampleUpdateDTO(name="test"))
        assert result is None


class TestRepositorySoftDelete:
    """Property tests for repository soft delete."""

    @settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow])
    @given(create_data=create_dto_strategy)
    @pytest.mark.asyncio
    async def test_soft_delete_behavior(self, create_data: SampleCreateDTO) -> None:
        """
        **Feature: generic-fastapi-crud, Property 8: Repository Soft Delete Behavior**
        """
        repo = InMemoryRepository[SampleEntity, SampleCreateDTO, SampleUpdateDTO](SampleEntity)

        created = await repo.create(create_data)
        deleted = await repo.delete(created.id)
        assert deleted is True

        retrieved = await repo.get_by_id(created.id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_returns_false(self) -> None:
        """Delete on non-existent entity SHALL return False."""
        repo = InMemoryRepository[SampleEntity, SampleCreateDTO, SampleUpdateDTO](SampleEntity)
        result = await repo.delete("nonexistent")
        assert result is False


class TestRepositoryPagination:
    """Property tests for repository pagination."""

    @settings(max_examples=20, suppress_health_check=[HealthCheck.too_slow])
    @given(
        items=st.lists(create_dto_strategy, min_size=1, max_size=30),
        skip=st.integers(min_value=0, max_value=10),
        limit=st.integers(min_value=1, max_value=10),
    )
    @pytest.mark.asyncio
    async def test_pagination_bounds(
        self, items: list[SampleCreateDTO], skip: int, limit: int
    ) -> None:
        """
        **Feature: generic-fastapi-crud, Property 9: Repository Pagination Bounds**
        """
        repo = InMemoryRepository[SampleEntity, SampleCreateDTO, SampleUpdateDTO](SampleEntity)

        for item in items:
            await repo.create(item)

        entities, total = await repo.get_all(skip=skip, limit=limit)

        assert total == len(items)
        assert len(entities) <= limit


class TestRepositoryBulkCreate:
    """Property tests for repository bulk create."""

    @settings(max_examples=20, suppress_health_check=[HealthCheck.too_slow])
    @given(items=st.lists(create_dto_strategy, min_size=1, max_size=10))
    @pytest.mark.asyncio
    async def test_bulk_create_atomicity(self, items: list[SampleCreateDTO]) -> None:
        """
        **Feature: generic-fastapi-crud, Property 10: Bulk Create Atomicity**
        """
        repo = InMemoryRepository[SampleEntity, SampleCreateDTO, SampleUpdateDTO](SampleEntity)

        created = await repo.create_many(items)

        assert len(created) == len(items)
        ids = [e.id for e in created]
        assert len(set(ids)) == len(ids), "All IDs should be unique"
