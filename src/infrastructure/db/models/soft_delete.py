"""Enhanced Soft Delete with cascade and restore support."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol


@dataclass
class SoftDeleteConfig:
    """Soft delete configuration."""

    cascade_relations: list[str] = field(default_factory=list)
    restore_cascade: bool = True
    permanent_delete_after_days: int | None = None
    track_deleted_by: bool = True


@dataclass
class DeletedRecord[T]:
    """Wrapper for soft-deleted records."""

    id: str
    entity_type: str
    original_id: str
    data: T
    deleted_at: datetime
    deleted_by: str | None = None
    cascade_deleted: list[str] = field(default_factory=list)
    restore_token: str = ""


class SoftDeleteBackend[T](Protocol):
    """Protocol for soft delete storage."""

    async def mark_deleted(
        self, entity_type: str, entity_id: str, deleted_by: str | None
    ) -> None: ...
    async def restore(self, entity_type: str, entity_id: str) -> bool: ...
    async def is_deleted(self, entity_type: str, entity_id: str) -> bool: ...
    async def get_deleted(self, entity_type: str) -> list[DeletedRecord[T]]: ...
    async def permanent_delete(self, entity_type: str, entity_id: str) -> bool: ...


class RelationResolver(Protocol):
    """Protocol for resolving entity relations."""

    async def get_dependents(
        self, entity_type: str, entity_id: str, relation: str
    ) -> list[tuple[str, str]]: ...


class SoftDeleteService[T]:
    """Service for soft delete with cascade support."""

    def __init__(
        self,
        backend: SoftDeleteBackend[T],
        relation_resolver: RelationResolver | None = None,
    ) -> None:
        self._backend = backend
        self._resolver = relation_resolver
        self._configs: dict[str, SoftDeleteConfig] = {}
        self._hooks: dict[str, list[Callable[[str, str], Awaitable[None]]]] = {
            "before_delete": [],
            "after_delete": [],
            "before_restore": [],
            "after_restore": [],
        }

    def configure(self, entity_type: str, config: SoftDeleteConfig) -> None:
        """Configure soft delete for an entity type."""
        self._configs[entity_type] = config

    def register_hook(
        self, event: str, callback: Callable[[str, str], Awaitable[None]]
    ) -> None:
        """Register a hook for delete/restore events."""
        if event in self._hooks:
            self._hooks[event].append(callback)

    async def _run_hooks(self, event: str, entity_type: str, entity_id: str) -> None:
        for hook in self._hooks.get(event, []):
            await hook(entity_type, entity_id)

    async def delete(
        self, entity_type: str, entity_id: str, deleted_by: str | None = None
    ) -> list[tuple[str, str]]:
        """Soft delete an entity with cascade."""
        await self._run_hooks("before_delete", entity_type, entity_id)

        deleted_entities: list[tuple[str, str]] = [(entity_type, entity_id)]
        config = self._configs.get(entity_type, SoftDeleteConfig())

        # Cascade delete
        if self._resolver and config.cascade_relations:
            for relation in config.cascade_relations:
                dependents = await self._resolver.get_dependents(
                    entity_type, entity_id, relation
                )
                for dep_type, dep_id in dependents:
                    await self._backend.mark_deleted(dep_type, dep_id, deleted_by)
                    deleted_entities.append((dep_type, dep_id))

        await self._backend.mark_deleted(entity_type, entity_id, deleted_by)
        await self._run_hooks("after_delete", entity_type, entity_id)

        return deleted_entities

    async def restore(self, entity_type: str, entity_id: str) -> list[tuple[str, str]]:
        """Restore a soft-deleted entity with cascade."""
        await self._run_hooks("before_restore", entity_type, entity_id)

        restored_entities: list[tuple[str, str]] = [(entity_type, entity_id)]
        config = self._configs.get(entity_type, SoftDeleteConfig())

        await self._backend.restore(entity_type, entity_id)

        # Cascade restore
        if self._resolver and config.restore_cascade and config.cascade_relations:
            for relation in config.cascade_relations:
                dependents = await self._resolver.get_dependents(
                    entity_type, entity_id, relation
                )
                for dep_type, dep_id in dependents:
                    if await self._backend.is_deleted(dep_type, dep_id):
                        await self._backend.restore(dep_type, dep_id)
                        restored_entities.append((dep_type, dep_id))

        await self._run_hooks("after_restore", entity_type, entity_id)
        return restored_entities

    async def is_deleted(self, entity_type: str, entity_id: str) -> bool:
        """Check if an entity is soft-deleted."""
        return await self._backend.is_deleted(entity_type, entity_id)

    async def get_deleted_records(self, entity_type: str) -> list[DeletedRecord[T]]:
        """Get all soft-deleted records of a type."""
        return await self._backend.get_deleted(entity_type)

    async def permanent_delete(self, entity_type: str, entity_id: str) -> bool:
        """Permanently delete a soft-deleted entity."""
        return await self._backend.permanent_delete(entity_type, entity_id)

    async def cleanup_expired(self, entity_type: str) -> int:
        """Permanently delete records past retention period."""
        config = self._configs.get(entity_type)
        if not config or not config.permanent_delete_after_days:
            return 0

        from datetime import timedelta

        cutoff = datetime.now(UTC) - timedelta(days=config.permanent_delete_after_days)
        deleted_count = 0

        records = await self._backend.get_deleted(entity_type)
        for record in records:
            if record.deleted_at < cutoff:
                await self._backend.permanent_delete(entity_type, record.original_id)
                deleted_count += 1

        return deleted_count


class InMemorySoftDeleteBackend[T]:
    """In-memory soft delete backend for testing."""

    def __init__(self) -> None:
        self._deleted: dict[tuple[str, str], DeletedRecord[T]] = {}

    async def mark_deleted(
        self, entity_type: str, entity_id: str, deleted_by: str | None
    ) -> None:
        import uuid

        key = (entity_type, entity_id)
        self._deleted[key] = DeletedRecord(
            id=str(uuid.uuid4()),
            entity_type=entity_type,
            original_id=entity_id,
            data=None,  # type: ignore
            deleted_at=datetime.now(UTC),
            deleted_by=deleted_by,
        )

    async def restore(self, entity_type: str, entity_id: str) -> bool:
        key = (entity_type, entity_id)
        if key in self._deleted:
            del self._deleted[key]
            return True
        return False

    async def is_deleted(self, entity_type: str, entity_id: str) -> bool:
        return (entity_type, entity_id) in self._deleted

    async def get_deleted(self, entity_type: str) -> list[DeletedRecord[T]]:
        return [r for r in self._deleted.values() if r.entity_type == entity_type]

    async def permanent_delete(self, entity_type: str, entity_id: str) -> bool:
        key = (entity_type, entity_id)
        if key in self._deleted:
            del self._deleted[key]
            return True
        return False
