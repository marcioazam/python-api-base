"""Property-based tests for Soft Delete Service.

**Feature: api-architecture-analysis, Property: Soft delete operations**
**Validates: Requirements 19.5**
"""

import pytest
from hypothesis import given, strategies as st, settings
from dataclasses import dataclass

from my_api.shared.soft_delete import (
    SoftDeleteService,
    SoftDeleteConfig,
    InMemorySoftDeleteBackend,
)


@dataclass
class SoftDeleteEntity:
    """Entity for soft delete testing."""
    id: str
    name: str


class TestSoftDeleteProperties:
    """Property tests for soft delete."""

    @given(
        st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=20),
        st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789", min_size=1, max_size=20)
    )
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_delete_marks_as_deleted(
        self,
        entity_type: str,
        entity_id: str
    ) -> None:
        """Delete marks entity as deleted."""
        backend: InMemorySoftDeleteBackend[TestEntity] = InMemorySoftDeleteBackend()
        service: SoftDeleteService[TestEntity] = SoftDeleteService(backend)

        await service.delete(entity_type, entity_id)

        assert await service.is_deleted(entity_type, entity_id)

    @given(
        st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=20),
        st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789", min_size=1, max_size=20)
    )
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_restore_unmarks_deleted(
        self,
        entity_type: str,
        entity_id: str
    ) -> None:
        """Restore unmarks entity as deleted."""
        backend: InMemorySoftDeleteBackend[TestEntity] = InMemorySoftDeleteBackend()
        service: SoftDeleteService[TestEntity] = SoftDeleteService(backend)

        await service.delete(entity_type, entity_id)
        await service.restore(entity_type, entity_id)

        assert not await service.is_deleted(entity_type, entity_id)

    @given(
        st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=20),
        st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789", min_size=1, max_size=20)
    )
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_delete_restore_round_trip(
        self,
        entity_type: str,
        entity_id: str
    ) -> None:
        """Delete then restore returns to original state."""
        backend: InMemorySoftDeleteBackend[TestEntity] = InMemorySoftDeleteBackend()
        service: SoftDeleteService[TestEntity] = SoftDeleteService(backend)

        initial_deleted = await service.is_deleted(entity_type, entity_id)
        await service.delete(entity_type, entity_id)
        await service.restore(entity_type, entity_id)
        final_deleted = await service.is_deleted(entity_type, entity_id)

        assert initial_deleted == final_deleted

    @given(
        st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=20),
        st.lists(
            st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789", min_size=1, max_size=20),
            min_size=1,
            max_size=10,
            unique=True
        )
    )
    @settings(max_examples=50)
    @pytest.mark.asyncio
    async def test_multiple_deletes_tracked(
        self,
        entity_type: str,
        entity_ids: list[str]
    ) -> None:
        """Multiple deletes are all tracked."""
        backend: InMemorySoftDeleteBackend[TestEntity] = InMemorySoftDeleteBackend()
        service: SoftDeleteService[TestEntity] = SoftDeleteService(backend)

        for entity_id in entity_ids:
            await service.delete(entity_type, entity_id)

        deleted_records = await service.get_deleted_records(entity_type)
        deleted_ids = {r.original_id for r in deleted_records}

        assert deleted_ids == set(entity_ids)

    @given(
        st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=20),
        st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789", min_size=1, max_size=20)
    )
    @settings(max_examples=50)
    @pytest.mark.asyncio
    async def test_permanent_delete_removes_record(
        self,
        entity_type: str,
        entity_id: str
    ) -> None:
        """Permanent delete removes from deleted records."""
        backend: InMemorySoftDeleteBackend[TestEntity] = InMemorySoftDeleteBackend()
        service: SoftDeleteService[TestEntity] = SoftDeleteService(backend)

        await service.delete(entity_type, entity_id)
        await service.permanent_delete(entity_type, entity_id)

        assert not await service.is_deleted(entity_type, entity_id)
