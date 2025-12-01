"""Batch operations for optimized bulk data processing.

Provides generic batch repository operations with chunking, parallel execution,
and error handling for high-performance mass operations.

Uses PEP 695 type parameter syntax (Python 3.12+).

**Feature: enterprise-features-2025**
**Refactored: Split into interfaces.py + repository.py for SRP compliance**
"""

from .builder import BatchOperationBuilder
from .config import (
    BatchConfig,
    BatchErrorStrategy,
    BatchOperationStats,
    BatchOperationType,
    BatchProgress,
    BatchResult,
    ChunkProcessor,
    ProgressCallback,
)
from .interfaces import (
    IBatchRepository,
    chunk_sequence,
    iter_chunks,
)
from .repository import BatchRepository

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
