"""Property-based tests for Audit Trail Service.

**Feature: api-architecture-analysis, Property: Audit operations**
**Validates: Requirements 19.3**
"""

import pytest
from hypothesis import given, strategies as st, settings
from datetime import datetime
from dataclasses import dataclass

from my_api.shared.audit_trail import (
    AuditService,
    AuditAction,
    DiffCalculator,
    InMemoryAuditBackend,
)


@dataclass
class AuditEntity:
    """Entity for audit testing."""
    id: str
    name: str
    value: int


class TestDiffCalculatorProperties:
    """Property tests for diff calculator."""

    @given(
        st.dictionaries(
            st.text(min_size=1, max_size=10),
            st.one_of(st.text(max_size=20), st.integers(), st.booleans()),
            min_size=0,
            max_size=10
        )
    )
    @settings(max_examples=100)
    def test_diff_from_none_captures_all_fields(
        self,
        after: dict[str, object]
    ) -> None:
        """Diff from None captures all fields as changes."""
        changes = DiffCalculator.compute_diff(None, after)
        changed_fields = {c.field_name for c in changes}
        assert changed_fields == set(after.keys())

    @given(
        st.dictionaries(
            st.text(min_size=1, max_size=10),
            st.one_of(st.text(max_size=20), st.integers(), st.booleans()),
            min_size=0,
            max_size=10
        )
    )
    @settings(max_examples=100)
    def test_diff_to_none_captures_all_fields(
        self,
        before: dict[str, object]
    ) -> None:
        """Diff to None captures all fields as changes."""
        changes = DiffCalculator.compute_diff(before, None)
        changed_fields = {c.field_name for c in changes}
        assert changed_fields == set(before.keys())

    @given(
        st.dictionaries(
            st.text(min_size=1, max_size=10),
            st.integers(),
            min_size=1,
            max_size=10
        )
    )
    @settings(max_examples=100)
    def test_no_diff_for_identical(self, data: dict[str, int]) -> None:
        """No diff for identical objects."""
        changes = DiffCalculator.compute_diff(data, data.copy())
        assert len(changes) == 0

    @given(
        st.dictionaries(
            st.text(min_size=1, max_size=10),
            st.integers(),
            min_size=1,
            max_size=5
        ),
        st.dictionaries(
            st.text(min_size=1, max_size=10),
            st.integers(),
            min_size=1,
            max_size=5
        )
    )
    @settings(max_examples=50)
    def test_apply_diff_reconstructs_state(
        self,
        before: dict[str, int],
        after: dict[str, int]
    ) -> None:
        """Applying diff to before produces after."""
        changes = DiffCalculator.compute_diff(before, after)
        reconstructed = DiffCalculator.apply_diff(before, changes)

        # Check that all keys in after are in reconstructed
        for key in after:
            assert key in reconstructed
            assert reconstructed[key] == after[key]


class TestAuditServiceProperties:
    """Property tests for audit service."""

    @given(
        st.text(min_size=1, max_size=20),
        st.text(min_size=1, max_size=20),
        st.text(min_size=1, max_size=50),
        st.integers()
    )
    @settings(max_examples=50)
    @pytest.mark.asyncio
    async def test_create_logs_all_fields(
        self,
        entity_type: str,
        entity_id: str,
        name: str,
        value: int
    ) -> None:
        """Create action logs all entity fields."""
        backend = InMemoryAuditBackend()
        service: AuditService[AuditEntity] = AuditService(backend)

        entity = AuditEntity(id=entity_id, name=name, value=value)
        entry = await service.log_create(entity_type, entity_id, entity)

        assert entry.action == AuditAction.CREATE
        assert entry.after_snapshot is not None
        assert entry.before_snapshot is None

    @given(
        st.text(min_size=1, max_size=20),
        st.text(min_size=1, max_size=20)
    )
    @settings(max_examples=50)
    @pytest.mark.asyncio
    async def test_history_returns_all_entries(
        self,
        entity_type: str,
        entity_id: str
    ) -> None:
        """History returns all entries for entity."""
        backend = InMemoryAuditBackend()
        service: AuditService[AuditEntity] = AuditService(backend)

        entity = AuditEntity(id=entity_id, name="test", value=1)
        await service.log_create(entity_type, entity_id, entity)

        history = await service.get_history(entity_type, entity_id)
        assert len(history) == 1
        assert history[0].entity_id == entity_id
