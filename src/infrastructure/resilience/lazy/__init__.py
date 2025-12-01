"""Lazy loading proxy for deferred entity loading.

**Feature: file-size-compliance-phase2, Task 2.5**
**Validates: Requirements 1.5, 5.1, 5.2, 5.3**

Provides a generic proxy pattern for lazy loading entities from repositories,
reducing unnecessary database queries by deferring loading until first access.
"""

from .enums import LoadState
from .loader import BatchLoader, lazy_collection, lazy_load
from .proxy import LazyCollection, LazyProxy, LazyRef

__all__ = [
    "BatchLoader",
    "LazyCollection",
    "LazyProxy",
    "LazyRef",
    "LoadState",
    "lazy_collection",
    "lazy_load",
]
