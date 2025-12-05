"""Batch operations for optimized bulk data processing.

Provides generic batch repository operations with chunking, parallel execution,
and error handling for high-performance mass operations.

Uses PEP 695 type parameter syntax (Python 3.12+).

**Architecture:**
- config/: Configuration types, enums, and result models
- interfaces/: Abstract batch repository interface and chunking utilities
- builders/: Fluent builder pattern for batch operation configuration
- repositories/: Concrete in-memory batch repository implementation

**Feature: enterprise-features-2025**
**Refactored: Organized into subpackages by responsibility (2025)**
"""

from application.common.batch.builders import BatchOperationBuilder
from application.common.batch.config import (
    BatchConfig,
    BatchErrorStrategy,
    BatchOperationStats,
    BatchOperationType,
    BatchProgress,
    BatchResult,
    ChunkProcessor,
    ProgressCallback,
)
from application.common.batch.interfaces import (
    IBatchRepository,
    chunk_sequence,
    iter_chunks,
)
from application.common.batch.repositories import BatchRepository

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
