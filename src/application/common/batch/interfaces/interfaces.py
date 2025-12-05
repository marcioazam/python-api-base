"""Batch operation interfaces and utilities.

This module provides:
- IBatchRepository interface for batch operations
- Utility functions for chunking sequences

**Feature: enterprise-features-2025**
**Validates: Requirements 10.1, 10.2**
**Refactored: Split from repository.py for SRP compliance**
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Sequence

from pydantic import BaseModel

from application.common.batch.config.config import (
    BatchConfig,
    BatchResult,
    ProgressCallback,
)

# =============================================================================
# Utility Functions
# =============================================================================


def chunk_sequence[T](items: Sequence[T], chunk_size: int) -> list[Sequence[T]]:
    """Split a sequence into chunks of specified size.

    Args:
        items: Sequence to split.
        chunk_size: Maximum size of each chunk.

    Returns:
        List of chunks.

    Raises:
        ValueError: If chunk_size is not positive.

    Example:
        >>> chunk_sequence([1, 2, 3, 4, 5], 2)
        [[1, 2], [3, 4], [5]]
    """
    if chunk_size <= 0:
        msg = "chunk_size must be positive"
        raise ValueError(msg)
    return [items[i : i + chunk_size] for i in range(0, len(items), chunk_size)]


async def iter_chunks[T](
    items: Sequence[T],
    chunk_size: int,
) -> AsyncIterator[tuple[int, Sequence[T]]]:
    """Async iterator over chunks with index.

    Args:
        items: Sequence to iterate over.
        chunk_size: Size of each chunk.

    Yields:
        Tuple of (chunk_index, chunk_items).
    """
    chunks = chunk_sequence(items, chunk_size)
    for idx, chunk in enumerate(chunks):
        yield idx, chunk


# =============================================================================
# Batch Repository Interface
# =============================================================================


class IBatchRepository[T: BaseModel, CreateT: BaseModel, UpdateT: BaseModel](ABC):
    """Interface for batch repository operations.

    Provides bulk CRUD operations with configurable error handling
    and progress tracking.

    Type Parameters:
        T: Entity type.
        CreateT: DTO type for creating entities.
        UpdateT: DTO type for updating entities.

    **Feature: enterprise-features-2025**
    **Validates: Requirements 10.1**
    """

    @abstractmethod
    async def bulk_create(
        self,
        items: Sequence[CreateT],
        *,
        config: BatchConfig | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> BatchResult[T]:
        """Create multiple entities in bulk.

        Args:
            items: Entities to create.
            config: Batch operation configuration.
            on_progress: Progress callback function.

        Returns:
            BatchResult with succeeded and failed items.
        """
        ...

    @abstractmethod
    async def bulk_update(
        self,
        items: Sequence[tuple[str, UpdateT]],
        *,
        config: BatchConfig | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> BatchResult[T]:
        """Update multiple entities in bulk.

        Args:
            items: Tuples of (entity_id, update_data).
            config: Batch operation configuration.
            on_progress: Progress callback function.

        Returns:
            BatchResult with succeeded and failed items.
        """
        ...

    @abstractmethod
    async def bulk_delete(
        self,
        ids: Sequence[str],
        *,
        soft: bool = True,
        config: BatchConfig | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> BatchResult[str]:
        """Delete multiple entities in bulk.

        Args:
            ids: Entity IDs to delete.
            soft: If True, soft delete; otherwise hard delete.
            config: Batch operation configuration.
            on_progress: Progress callback function.

        Returns:
            BatchResult with succeeded and failed IDs.
        """
        ...

    @abstractmethod
    async def bulk_get(
        self,
        ids: Sequence[str],
        *,
        config: BatchConfig | None = None,
    ) -> dict[str, T | None]:
        """Get multiple entities by IDs.

        Args:
            ids: Entity IDs to retrieve.
            config: Batch operation configuration.

        Returns:
            Dict mapping ID to entity or None.
        """
        ...

    @abstractmethod
    async def bulk_exists(
        self,
        ids: Sequence[str],
        *,
        config: BatchConfig | None = None,
    ) -> dict[str, bool]:
        """Check existence of multiple entities.

        Args:
            ids: Entity IDs to check.
            config: Batch operation configuration.

        Returns:
            Dict mapping ID to existence status.
        """
        ...

    @abstractmethod
    async def bulk_upsert(
        self,
        items: Sequence[CreateT],
        *,
        key_field: str = "id",
        config: BatchConfig | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> BatchResult[T]:
        """Insert or update multiple entities.

        Args:
            items: Entities to upsert.
            key_field: Field to use as unique key.
            config: Batch operation configuration.
            on_progress: Progress callback function.

        Returns:
            BatchResult with succeeded and failed items.
        """
        ...
