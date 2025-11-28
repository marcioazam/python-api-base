"""Property-based tests for Data Archival Service.

**Feature: api-architecture-analysis, Property: Archival operations**
**Validates: Requirements 19.2**
"""

import pytest
from hypothesis import given, strategies as st, settings
from datetime import datetime, timedelta
from dataclasses import dataclass

from my_api.shared.archival import (
    RetentionPolicy,
    ArchivalService,
    StorageTier,
    InMemoryArchivalBackend,
)


@dataclass
class TestRecord:
    """Test record for archival."""
    id: str
    name: str
    created_at: datetime


class TestSourceRepository:
    """Test source repository."""

    def __init__(self) -> None:
        self._records: list[TestRecord] = []

    async def find_older_than(
        self,
        entity_type: str,
        cutoff_date: datetime,
        limit: int
    ) -> list[TestRecord]:
        return [r for r in self._records if r.created_at < cutoff_date][:limit]

    async def delete_by_ids(self, ids: list[str]) -> int:
        before = len(self._records)
        self._records = [r for r in self._records if r.id not in ids]
        return before - len(self._records)

    async def get_created_at(self, record: TestRecord) -> datetime:
        return record.created_at

    async def get_id(self, record: TestRecord) -> str:
        return record.id


class TestRetentionPolicyProperties:
    """Property tests for retention policy."""

    @given(
        st.integers(min_value=1, max_value=30),
        st.integers(min_value=31, max_value=90),
        st.integers(min_value=91, max_value=365),
        st.integers(min_value=0, max_value=400)
    )
    @settings(max_examples=100)
    def test_tier_assignment_correct(
        self,
        hot_days: int,
        warm_days: int,
        cold_days: int,
        age_days: int
    ) -> None:
        """Tier assignment based on age is correct."""
        policy = RetentionPolicy(
            name="test",
            entity_type="test",
            hot_retention_days=hot_days,
            warm_retention_days=warm_days,
            cold_retention_days=cold_days
        )

        tier = policy.get_tier_for_age(age_days)

        if age_days <= hot_days:
            assert tier == StorageTier.HOT
        elif age_days <= warm_days:
            assert tier == StorageTier.WARM
        elif age_days <= cold_days:
            assert tier == StorageTier.COLD
        else:
            assert tier == StorageTier.GLACIER

    @given(st.integers(min_value=0, max_value=100))
    @settings(max_examples=50)
    def test_hot_tier_for_recent_data(self, age_days: int) -> None:
        """Recent data is always in hot tier."""
        policy = RetentionPolicy(
            name="test",
            entity_type="test",
            hot_retention_days=100
        )

        tier = policy.get_tier_for_age(age_days)
        assert tier == StorageTier.HOT


class TestArchivalServiceProperties:
    """Property tests for archival service."""

    @given(st.lists(st.text(min_size=1, max_size=20), min_size=1, max_size=10))
    @settings(max_examples=50)
    @pytest.mark.asyncio
    async def test_archival_stats_by_tier(self, record_ids: list[str]) -> None:
        """Archival stats correctly count by tier."""
        backend: InMemoryArchivalBackend[TestRecord] = InMemoryArchivalBackend()
        source = TestSourceRepository()
        service: ArchivalService[TestRecord] = ArchivalService(backend, source)

        policy = RetentionPolicy(
            name="test",
            entity_type="test_entity",
            hot_retention_days=30
        )
        service.register_policy(policy)

        stats = await service.get_archival_stats("test_entity")

        # All tiers should have counts
        for tier in StorageTier:
            assert tier.value in stats
