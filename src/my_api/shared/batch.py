"""Batch operations for optimized bulk data processing.

This module has been refactored into a package for better maintainability.
All exports are re-exported from the package for backward compatibility.

See: src/my_api/shared/batch/
"""

# Re-export all public APIs for backward compatibility
from my_api.shared.batch import (
    BatchConfig,
    BatchErrorStrategy,
    BatchOperationBuilder,
    BatchOperationStats,
    BatchOperationType,
    BatchProgress,
    BatchRepository,
    BatchResult,
    ChunkProcessor,
    IBatchRepository,
    ProgressCallback,
    chunk_sequence,
    iter_chunks,
)

__all__ = [
    "BatchConfig",
    "BatchErrorStrategy",
    "BatchOperationBuilder",
    "BatchOperationStats",
    "BatchOperationType",
    "BatchProgress",
    "BatchRepository",
    "BatchResult",
    "ChunkProcessor",
    "IBatchRepository",
    "ProgressCallback",
    "chunk_sequence",
    "iter_chunks",
]
