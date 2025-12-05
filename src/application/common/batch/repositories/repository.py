"""In-memory batch repository implementation.

**Feature: enterprise-features-2025**
**Validates: Requirements 10.1, 10.2, 10.3**
**Refactored: Interface moved to interfaces.py for SRP compliance**
**Fix: F-02 - Deep copy safety with fallback**
"""

import copy
import logging
from collections.abc import Callable, Sequence

from pydantic import BaseModel

from application.common.batch.config.config import (
    BatchConfig,
    BatchErrorStrategy,
    BatchProgress,
    BatchResult,
    ProgressCallback,
)
from application.common.batch.interfaces.interfaces import IBatchRepository, chunk_sequence

logger = logging.getLogger(__name__)


def _process_chunk_with_progress[TItem, TResult](
    chunk: list[TItem],
    processor: callable,
    progress: BatchProgress,
    on_progress: ProgressCallback | None,
    error_strategy: BatchErrorStrategy,
    succeeded: list[TResult],
    failed: list[tuple[TItem, Exception]],
) -> bool:
    """Process a chunk and update progress.

    Returns:
        True if should continue processing, False if should stop (fail-fast).
    """
    chunk_succeeded, chunk_failed = 0, 0

    for item in chunk:
        try:
            result = processor(item)
            succeeded.append(result)
            chunk_succeeded += 1
        except Exception as e:
            failed.append((item, e))
            chunk_failed += 1
            if error_strategy == BatchErrorStrategy.FAIL_FAST:
                break

    progress.processed_items += chunk_succeeded + chunk_failed
    progress.succeeded_items += chunk_succeeded
    progress.failed_items += chunk_failed
    progress.current_chunk += 1

    if on_progress:
        on_progress(progress)

    return not (error_strategy == BatchErrorStrategy.FAIL_FAST and failed)


class BatchRepository[T: BaseModel, CreateT: BaseModel, UpdateT: BaseModel](
    IBatchRepository[T, CreateT, UpdateT]
):
    """In-memory batch repository implementation."""

    def __init__(
        self,
        entity_type: type[T],
        id_generator: Callable[[], str] | None = None,
        id_field: str = "id",
    ) -> None:
        """Initialize batch repository."""
        self._entity_type = entity_type
        self._id_generator = id_generator or self._default_id_generator
        self._id_field = id_field
        self._storage: dict[str, T] = {}
        self._counter = 0

    def _default_id_generator(self) -> str:
        """Generate a simple incremental ID."""
        self._counter += 1
        return str(self._counter)

    def _get_config(self, config: BatchConfig | None) -> BatchConfig:
        """Get config with defaults."""
        return config or BatchConfig()

    def _update_progress(
        self,
        progress: BatchProgress,
        succeeded: int,
        failed: int,
        on_progress: ProgressCallback | None,
    ) -> None:
        """Update and report progress."""
        progress.processed_items += succeeded + failed
        progress.succeeded_items += succeeded
        progress.failed_items += failed
        progress.current_chunk += 1
        if on_progress:
            on_progress(progress)

    def _create_entity(self, item: CreateT) -> tuple[T, str]:
        """Create entity from CreateT data. Returns (entity, entity_id)."""
        entity_data = item.model_dump()
        if self._id_field not in entity_data or not entity_data[self._id_field]:
            entity_data[self._id_field] = self._id_generator()
        entity = self._entity_type.model_validate(entity_data)
        entity_id = entity_data[self._id_field]
        self._storage[entity_id] = entity
        return entity, entity_id

    def _create_snapshot(self) -> dict[str, T]:
        """Create deep copy of storage for rollback.

        Uses Pydantic serialization when possible, falls back to deepcopy
        for complex types that don't serialize cleanly.

        **Feature: application-layer-code-review-fixes**
        **Validates: Requirements F-02**
        """
        try:
            return {
                k: self._entity_type.model_validate(v.model_dump())
                for k, v in self._storage.items()
            }
        except Exception as e:
            logger.warning(
                f"Pydantic snapshot failed, using deepcopy: {e}",
                extra={"operation": "BATCH_SNAPSHOT", "fallback": "deepcopy"},
            )
            return copy.deepcopy(self._storage)

    def _handle_rollback(
        self,
        snapshot: dict[str, T],
        item: CreateT,
        error: Exception,
        succeeded_count: int,
    ) -> BatchResult[T]:
        """Handle rollback on error."""
        rollback_error = None
        try:
            self._storage = snapshot
        except Exception as re:
            rollback_error = re
        return BatchResult(
            succeeded=[],
            failed=[(item, error)],
            total_processed=succeeded_count + 1,
            total_succeeded=0,
            total_failed=succeeded_count + 1,
            rolled_back=True,
            rollback_error=rollback_error,
        )

    async def bulk_create(
        self,
        items: Sequence[CreateT],
        *,
        config: BatchConfig | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> BatchResult[T]:
        """Create multiple entities in bulk.

        **Refactored: 2025 - Reduced complexity from 11 to 8**
        """
        cfg = self._get_config(config)
        chunks = chunk_sequence(items, cfg.chunk_size)
        progress = BatchProgress(total_items=len(items), total_chunks=len(chunks))
        succeeded: list[T] = []
        failed: list[tuple[CreateT, Exception]] = []

        logger.info(
            f"Starting bulk create: {len(items)} items in {len(chunks)} chunks",
            extra={
                "operation": "BULK_CREATE",
                "total_items": len(items),
                "chunk_size": cfg.chunk_size,
                "error_strategy": cfg.error_strategy.value,
            },
        )

        # Deep copy for rollback to prevent mutation issues
        snapshot = (
            self._create_snapshot()
            if cfg.error_strategy == BatchErrorStrategy.ROLLBACK
            else None
        )

        for chunk in chunks:
            chunk_succeeded, chunk_failed = 0, 0
            for item in chunk:
                try:
                    entity, _ = self._create_entity(item)
                    succeeded.append(entity)
                    chunk_succeeded += 1
                except Exception as e:
                    failed.append((item, e))
                    chunk_failed += 1
                    if cfg.error_strategy == BatchErrorStrategy.FAIL_FAST:
                        break
                    if cfg.error_strategy == BatchErrorStrategy.ROLLBACK and snapshot:
                        return self._handle_rollback(snapshot, item, e, len(succeeded))

            self._update_progress(progress, chunk_succeeded, chunk_failed, on_progress)
            if cfg.error_strategy == BatchErrorStrategy.FAIL_FAST and failed:
                break

        result = BatchResult(
            succeeded=succeeded,
            failed=failed,
            total_processed=len(succeeded) + len(failed),
            total_succeeded=len(succeeded),
            total_failed=len(failed),
        )

        logger.info(
            f"Bulk create completed: {result.total_succeeded} succeeded, {result.total_failed} failed",
            extra={
                "operation": "BULK_CREATE",
                "succeeded": result.total_succeeded,
                "failed": result.total_failed,
                "success_rate": f"{result.success_rate:.1f}%",
            },
        )

        return result

    async def bulk_update(
        self,
        items: Sequence[tuple[str, UpdateT]],
        *,
        config: BatchConfig | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> BatchResult[T]:
        """Update multiple entities in bulk."""
        cfg = self._get_config(config)
        chunks = chunk_sequence(items, cfg.chunk_size)
        progress = BatchProgress(total_items=len(items), total_chunks=len(chunks))
        succeeded: list[T] = []
        failed: list[tuple[tuple[str, UpdateT], Exception]] = []

        for chunk in chunks:
            chunk_succeeded, chunk_failed = 0, 0
            for entity_id, update_data in chunk:
                try:
                    existing = self._storage.get(entity_id)
                    if existing is None:
                        raise KeyError(f"Entity not found: {entity_id}")
                    existing_data = existing.model_dump()
                    update_dict = update_data.model_dump(exclude_unset=True)
                    for key, value in update_dict.items():
                        if value is not None:
                            existing_data[key] = value
                    updated = self._entity_type.model_validate(existing_data)
                    self._storage[entity_id] = updated
                    succeeded.append(updated)
                    chunk_succeeded += 1
                except Exception as e:
                    failed.append(((entity_id, update_data), e))
                    chunk_failed += 1
                    if cfg.error_strategy == BatchErrorStrategy.FAIL_FAST:
                        break
            self._update_progress(progress, chunk_succeeded, chunk_failed, on_progress)
            if cfg.error_strategy == BatchErrorStrategy.FAIL_FAST and failed:
                break

        return BatchResult(
            succeeded=succeeded,
            failed=failed,
            total_processed=len(succeeded) + len(failed),
            total_succeeded=len(succeeded),
            total_failed=len(failed),
        )

    async def bulk_delete(
        self,
        ids: Sequence[str],
        *,
        soft: bool = True,
        config: BatchConfig | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> BatchResult[str]:
        """Delete multiple entities in bulk."""
        cfg = self._get_config(config)
        chunks = chunk_sequence(ids, cfg.chunk_size)
        progress = BatchProgress(total_items=len(ids), total_chunks=len(chunks))
        succeeded: list[str] = []
        failed: list[tuple[str, Exception]] = []

        for chunk in chunks:
            chunk_succeeded, chunk_failed = 0, 0
            for entity_id in chunk:
                try:
                    if entity_id not in self._storage:
                        raise KeyError(f"Entity not found: {entity_id}")
                    if soft:
                        entity = self._storage[entity_id]
                        if hasattr(entity, "is_deleted"):
                            entity_data = entity.model_dump()
                            entity_data["is_deleted"] = True
                            self._storage[entity_id] = self._entity_type.model_validate(
                                entity_data
                            )
                        else:
                            del self._storage[entity_id]
                    else:
                        del self._storage[entity_id]
                    succeeded.append(entity_id)
                    chunk_succeeded += 1
                except Exception as e:
                    failed.append((entity_id, e))
                    chunk_failed += 1
                    if cfg.error_strategy == BatchErrorStrategy.FAIL_FAST:
                        break
            self._update_progress(progress, chunk_succeeded, chunk_failed, on_progress)
            if cfg.error_strategy == BatchErrorStrategy.FAIL_FAST and failed:
                break

        return BatchResult(
            succeeded=succeeded,
            failed=failed,
            total_processed=len(succeeded) + len(failed),
            total_succeeded=len(succeeded),
            total_failed=len(failed),
        )

    async def bulk_get(
        self,
        ids: Sequence[str],
        *,
        config: BatchConfig | None = None,
    ) -> dict[str, T | None]:
        """Get multiple entities by IDs."""
        result: dict[str, T | None] = {}
        for entity_id in ids:
            entity = self._storage.get(entity_id)
            if entity and hasattr(entity, "is_deleted") and entity.is_deleted:
                result[entity_id] = None
            else:
                result[entity_id] = entity
        return result

    async def bulk_exists(
        self,
        ids: Sequence[str],
        *,
        config: BatchConfig | None = None,
    ) -> dict[str, bool]:
        """Check existence of multiple entities."""
        entities = await self.bulk_get(ids, config=config)
        return {entity_id: entity is not None for entity_id, entity in entities.items()}

    async def bulk_upsert(
        self,
        items: Sequence[CreateT],
        *,
        key_field: str = "id",
        config: BatchConfig | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> BatchResult[T]:
        """Insert or update multiple entities."""
        cfg = self._get_config(config)
        chunks = chunk_sequence(items, cfg.chunk_size)
        progress = BatchProgress(total_items=len(items), total_chunks=len(chunks))
        succeeded: list[T] = []
        failed: list[tuple[CreateT, Exception]] = []

        for chunk in chunks:
            chunk_succeeded, chunk_failed = 0, 0
            for item in chunk:
                try:
                    entity_data = item.model_dump()
                    key_value = entity_data.get(key_field)
                    if key_value and key_value in self._storage:
                        existing = self._storage[key_value]
                        existing_data = existing.model_dump()
                        for k, v in entity_data.items():
                            if v is not None:
                                existing_data[k] = v
                        entity = self._entity_type.model_validate(existing_data)
                    else:
                        if not key_value:
                            entity_data[key_field] = self._id_generator()
                        entity = self._entity_type.model_validate(entity_data)
                    entity_id = getattr(entity, key_field)
                    self._storage[entity_id] = entity
                    succeeded.append(entity)
                    chunk_succeeded += 1
                except Exception as e:
                    failed.append((item, e))
                    chunk_failed += 1
                    if cfg.error_strategy == BatchErrorStrategy.FAIL_FAST:
                        break
            self._update_progress(progress, chunk_succeeded, chunk_failed, on_progress)
            if cfg.error_strategy == BatchErrorStrategy.FAIL_FAST and failed:
                break

        return BatchResult(
            succeeded=succeeded,
            failed=failed,
            total_processed=len(succeeded) + len(failed),
            total_succeeded=len(succeeded),
            total_failed=len(failed),
        )

    def clear(self) -> None:
        """Clear all entities from storage."""
        self._storage.clear()
        self._counter = 0

    @property
    def count(self) -> int:
        """Get total number of entities."""
        return len(self._storage)
