"""Generic ScyllaDB infrastructure.

Provides type-safe ScyllaDB operations with PEP 695 generics.

**Feature: observability-infrastructure**
**Requirement: R4 - Generic ScyllaDB Repository**
"""

from infrastructure.scylladb.config import ScyllaDBConfig
from infrastructure.scylladb.client import ScyllaDBClient
from infrastructure.scylladb.entity import ScyllaDBEntity
from infrastructure.scylladb.repository import ScyllaDBRepository

__all__ = [
    "ScyllaDBConfig",
    "ScyllaDBClient",
    "ScyllaDBEntity",
    "ScyllaDBRepository",
]
