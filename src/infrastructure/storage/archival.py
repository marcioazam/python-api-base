"""Data Archival Service with configurable retention policies."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Protocol, Any
from collections.abc import Callable, Awaitable
import json


class ArchivalStrategy(Enum):
    """Strategy for archiving data."""
    DELETE = "delete"
    MOVE_TO_COLD = "move_to_cold"
    COMPRESS = "compress"
    EXPORT = "export"


class StorageTier(Enum):
    """Storage tier for archived data."""
    HOT = "hot"
    WARM = "warm"
    COLD = "cold"
    GLACIER = "glacier"


@dataclass
class RetentionPolicy:
    """Retention policy configuration."""
    name: str
    entity_type: str
    hot_retention_days: int = 30
    warm_retention_days: int = 90
    cold_retention_days: int = 365
    archive_strategy: ArchivalStrategy = ArchivalStrategy.MOVE_TO_COLD
    delete_after_days: int | None = None
    filter_condition: str | None = None

    def get_tier_for_age(self, age_days: int) -> StorageTier:
        """Determine storage tier based on data age."""
        if age_days <= self.hot_retention_days:
            return StorageTier.HOT
        elif age_days <= self.warm_retention_days:
            return StorageTier.WARM
        elif age_days <= self.cold_retention_days:
            return StorageTier.COLD
        return StorageTier.GLACIER


@dataclass
class ArchivalJob:
    """Archival job definition."""
    id: str
    policy: RetentionPolicy
    started_at: datetime
    completed_at: datetime | None = None
    records_processed: int = 0
    records_archived: int = 0
    records_deleted: int = 0
    errors: list[str] = field(default_factory=list)
    status: str = "running"


@dataclass
class ArchivedRecord[T]:
    """Archived record wrapper."""
    id: str
    entity_type: str
    original_id: str
    data: T
    archived_at: datetime
    original_created_at: datetime
    tier: StorageTier
    checksum: str
    metadata: dict[str, Any] = field(default_factory=dict)


class ArchivalBackend[T](Protocol):
    """Protocol for archival storage backend."""

    async def store(self, record: ArchivedRecord[T]) -> None: ...
    async def retrieve(self, id: str) -> ArchivedRecord[T] | None: ...
    async def delete(self, id: str) -> bool: ...
    async def list_by_tier(self, tier: StorageTier) -> list[ArchivedRecord[T]]: ...
    async def move_tier(self, id: str, new_tier: StorageTier) -> bool: ...


class SourceRepository[T](Protocol):
    """Protocol for source data repository."""

    async def find_older_than(
        self,
        entity_type: str,
        cutoff_date: datetime,
        limit: int
    ) -> list[T]: ...

    async def delete_by_ids(self, ids: list[str]) -> int: ...
    async def get_created_at(self, record: T) -> datetime: ...
    async def get_id(self, record: T) -> str: ...


class ArchivalService[T]:
    """Service for archiving old data."""

    def __init__(
        self,
        backend: ArchivalBackend[T],
        source: SourceRepository[T]
    ) -> None:
        self._backend = backend
        self._source = source
        self._policies: dict[str, RetentionPolicy] = {}
        self._hooks: dict[str, list[Callable[[T], Awaitable[None]]]] = {
            "before_archive": [],
            "after_archive": [],
            "before_delete": [],
        }

    def register_policy(self, policy: RetentionPolicy) -> None:
        """Register a retention policy."""
        self._policies[policy.entity_type] = policy

    def register_hook(
        self,
        event: str,
        callback: Callable[[T], Awaitable[None]]
    ) -> None:
        """Register a hook for archival events."""
        if event in self._hooks:
            self._hooks[event].append(callback)

    async def _run_hooks(self, event: str, record: T) -> None:
        for hook in self._hooks.get(event, []):
            await hook(record)

    def _compute_checksum(self, data: Any) -> str:
        import hashlib
        content = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    async def run_archival(
        self,
        entity_type: str,
        batch_size: int = 1000
    ) -> ArchivalJob:
        """Run archival for an entity type."""
        import uuid

        policy = self._policies.get(entity_type)
        if not policy:
            raise ValueError(f"No policy for entity type: {entity_type}")

        job = ArchivalJob(
            id=str(uuid.uuid4()),
            policy=policy,
            started_at=datetime.now(timezone.utc)
        )

        try:
            cutoff = datetime.now(timezone.utc) - timedelta(days=policy.hot_retention_days)
            records = await self._source.find_older_than(
                entity_type, cutoff, batch_size
            )

            for record in records:
                job.records_processed += 1
                try:
                    await self._archive_record(record, policy)
                    job.records_archived += 1
                except Exception as e:
                    job.errors.append(str(e))

            if policy.delete_after_days:
                delete_cutoff = datetime.now(timezone.utc) - timedelta(
                    days=policy.delete_after_days
                )
                old_records = await self._source.find_older_than(
                    entity_type, delete_cutoff, batch_size
                )
                ids_to_delete = [
                    await self._source.get_id(r) for r in old_records
                ]
                if ids_to_delete:
                    for record in old_records:
                        await self._run_hooks("before_delete", record)
                    job.records_deleted = await self._source.delete_by_ids(
                        ids_to_delete
                    )

            job.status = "completed"

        except Exception as e:
            job.status = "failed"
            job.errors.append(str(e))

        job.completed_at = datetime.now(timezone.utc)
        return job

    async def _archive_record(
        self,
        record: T,
        policy: RetentionPolicy
    ) -> ArchivedRecord[T]:
        """Archive a single record."""
        import uuid

        await self._run_hooks("before_archive", record)

        created_at = await self._source.get_created_at(record)
        age_days = (datetime.now(timezone.utc) - created_at).days
        tier = policy.get_tier_for_age(age_days)

        archived = ArchivedRecord(
            id=str(uuid.uuid4()),
            entity_type=policy.entity_type,
            original_id=await self._source.get_id(record),
            data=record,
            archived_at=datetime.now(timezone.utc),
            original_created_at=created_at,
            tier=tier,
            checksum=self._compute_checksum(record)
        )

        await self._backend.store(archived)
        await self._run_hooks("after_archive", record)

        return archived

    async def restore(self, archived_id: str) -> T | None:
        """Restore an archived record."""
        archived = await self._backend.retrieve(archived_id)
        if archived:
            return archived.data
        return None

    async def get_archival_stats(
        self,
        entity_type: str
    ) -> dict[str, int]:
        """Get archival statistics."""
        stats: dict[str, int] = {}
        for tier in StorageTier:
            records = await self._backend.list_by_tier(tier)
            filtered = [r for r in records if r.entity_type == entity_type]
            stats[tier.value] = len(filtered)
        return stats

    async def migrate_tier(
        self,
        entity_type: str
    ) -> int:
        """Migrate records to appropriate tiers based on age."""
        migrated = 0
        policy = self._policies.get(entity_type)
        if not policy:
            return 0

        for tier in [StorageTier.HOT, StorageTier.WARM, StorageTier.COLD]:
            records = await self._backend.list_by_tier(tier)
            for record in records:
                if record.entity_type != entity_type:
                    continue

                age_days = (datetime.now(timezone.utc) - record.original_created_at).days
                expected_tier = policy.get_tier_for_age(age_days)

                if expected_tier != record.tier:
                    await self._backend.move_tier(record.id, expected_tier)
                    migrated += 1

        return migrated


class InMemoryArchivalBackend[T]:
    """In-memory archival backend for testing."""

    def __init__(self) -> None:
        self._records: dict[str, ArchivedRecord[T]] = {}

    async def store(self, record: ArchivedRecord[T]) -> None:
        self._records[record.id] = record

    async def retrieve(self, id: str) -> ArchivedRecord[T] | None:
        return self._records.get(id)

    async def delete(self, id: str) -> bool:
        if id in self._records:
            del self._records[id]
            return True
        return False

    async def list_by_tier(self, tier: StorageTier) -> list[ArchivedRecord[T]]:
        return [r for r in self._records.values() if r.tier == tier]

    async def move_tier(self, id: str, new_tier: StorageTier) -> bool:
        if id in self._records:
            self._records[id].tier = new_tier
            return True
        return False
