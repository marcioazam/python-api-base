"""Fluent builder for batch operations."""

from collections.abc import Sequence

from pydantic import BaseModel

from my_api.shared.batch.config import (
    BatchConfig,
    BatchErrorStrategy,
    BatchResult,
    ProgressCallback,
)
from my_api.shared.batch.repository import IBatchRepository


class BatchOperationBuilder[T: BaseModel, CreateT: BaseModel, UpdateT: BaseModel]:
    """Fluent builder for batch operations.

    Provides a chainable API for configuring and executing batch operations.
    """

    def __init__(self, repository: IBatchRepository[T, CreateT, UpdateT]) -> None:
        """Initialize builder with repository."""
        self._repository = repository
        self._config = BatchConfig()
        self._progress_callback: ProgressCallback | None = None

    def with_chunk_size(self, size: int) -> "BatchOperationBuilder[T, CreateT, UpdateT]":
        """Set chunk size for batch processing."""
        self._config.chunk_size = size
        return self

    def with_error_strategy(
        self, strategy: BatchErrorStrategy
    ) -> "BatchOperationBuilder[T, CreateT, UpdateT]":
        """Set error handling strategy."""
        self._config.error_strategy = strategy
        return self

    def with_retry(
        self, max_retries: int = 3
    ) -> "BatchOperationBuilder[T, CreateT, UpdateT]":
        """Enable retry for failed operations."""
        self._config.retry_failed = True
        self._config.max_retries = max_retries
        return self

    def with_progress(
        self, callback: ProgressCallback
    ) -> "BatchOperationBuilder[T, CreateT, UpdateT]":
        """Set progress callback."""
        self._progress_callback = callback
        return self

    async def create(self, items: Sequence[CreateT]) -> BatchResult[T]:
        """Execute bulk create operation."""
        return await self._repository.bulk_create(
            items, config=self._config, on_progress=self._progress_callback
        )

    async def update(self, items: Sequence[tuple[str, UpdateT]]) -> BatchResult[T]:
        """Execute bulk update operation."""
        return await self._repository.bulk_update(
            items, config=self._config, on_progress=self._progress_callback
        )

    async def delete(self, ids: Sequence[str], *, soft: bool = True) -> BatchResult[str]:
        """Execute bulk delete operation."""
        return await self._repository.bulk_delete(
            ids, soft=soft, config=self._config, on_progress=self._progress_callback
        )

    async def upsert(
        self, items: Sequence[CreateT], *, key_field: str = "id"
    ) -> BatchResult[T]:
        """Execute bulk upsert operation."""
        return await self._repository.bulk_upsert(
            items,
            key_field=key_field,
            config=self._config,
            on_progress=self._progress_callback,
        )
