"""Data access protocols.

Defines protocols for data access patterns including repositories,
caches, and unit of work for transaction management.

**Feature: core-protocols-restructuring-2025**
"""

from core.protocols.data_access.data_access import (
    AsyncRepository,
    CacheProvider,
    UnitOfWork,
)
from core.protocols.data_access.repository import AsyncRepository

__all__ = [
    "AsyncRepository",
    "CacheProvider",
    "UnitOfWork",
]
