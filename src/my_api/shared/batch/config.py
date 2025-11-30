"""Batch operation configuration and result types."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Any


class BatchOperationType(Enum):
    """Types of batch operations."""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    UPSERT = "upsert"


class BatchErrorStrategy(Enum):
    """Error handling strategies for batch operations."""

    FAIL_FAST = "fail_fast"  # Stop on first error
    CONTINUE = "continue"  # Continue and collect errors
    ROLLBACK = "rollback"  # Rollback all on any error


@dataclass(frozen=True, slots=True)
class BatchResult[T]:
    """Result of a batch operation.

    Type Parameters:
        T: Type of successfully processed items.

    **Feature: shared-modules-refactoring**
    **Validates: Requirements 10.1, 10.2, 10.3**
    """

    succeeded: Sequence[T]
    failed: Sequence[tuple[Any, Exception]]
    total_processed: int
    total_succeeded: int
    total_failed: int
    rolled_back: bool = False
    rollback_error: Exception | None = None

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_processed == 0:
            return 100.0
        return (self.total_succeeded / self.total_processed) * 100

    @property
    def is_complete_success(self) -> bool:
        """Check if all operations succeeded."""
        return self.total_failed == 0 and not self.rolled_back

    @property
    def has_failures(self) -> bool:
        """Check if any operations failed."""
        return self.total_failed > 0 or self.rolled_back


@dataclass(slots=True)
class BatchConfig:
    """Configuration for batch operations."""

    chunk_size: int = 100
    max_concurrent: int = 5
    error_strategy: BatchErrorStrategy = BatchErrorStrategy.CONTINUE
    retry_failed: bool = False
    max_retries: int = 3
    timeout_per_chunk: float | None = None


@dataclass(slots=True)
class BatchProgress:
    """Progress tracking for batch operations."""

    total_items: int
    processed_items: int = 0
    succeeded_items: int = 0
    failed_items: int = 0
    current_chunk: int = 0
    total_chunks: int = 0

    @property
    def progress_percentage(self) -> float:
        """Calculate progress as percentage."""
        if self.total_items == 0:
            return 100.0
        return (self.processed_items / self.total_items) * 100

    @property
    def is_complete(self) -> bool:
        """Check if batch processing is complete."""
        return self.processed_items >= self.total_items


@dataclass(slots=True)
class BatchOperationStats:
    """Statistics for batch operations."""

    operation_type: BatchOperationType
    total_items: int = 0
    succeeded: int = 0
    failed: int = 0
    duration_ms: float = 0.0
    items_per_second: float = 0.0
    chunks_processed: int = 0

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_items == 0:
            return 100.0
        return (self.succeeded / self.total_items) * 100


type ProgressCallback = Callable[[BatchProgress], None]
type ChunkProcessor[T, R] = Callable[[Sequence[T]], Sequence[R]]
