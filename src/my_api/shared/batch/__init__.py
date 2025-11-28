"""Batch operations for optimized bulk data processing.

Provides generic batch repository operations with chunking, parallel execution,
and error handling for high-performance mass operations.

Uses PEP 695 type parameter syntax (Python 3.12+).
"""

from my_api.shared.batch.config import (
    BatchConfig,
    BatchErrorStrategy,
    BatchOperationStats,
    BatchOperationType,
    BatchProgress,
    BatchResult,
    ChunkProcessor,
    ProgressCallback,
)
from my_api.shared.batch.repository import (
    BatchRepository,
    IBatchRepository,
    chunk_sequence,
    iter_chunks,
)
from my_api.shared.batch.builder import BatchOperationBuilder

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
