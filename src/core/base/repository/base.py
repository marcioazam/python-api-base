"""Generic repository interface for CRUD operations.

This module has been refactored into smaller, focused modules:
- base/pagination.py: Cursor-based pagination utilities
- base/repository_interface.py: IRepository abstract interface
- base/repository_memory.py: InMemoryRepository implementation for testing

This file now serves as a compatibility layer, re-exporting all components.

Uses PEP 695 type parameter syntax (Python 3.12+) for cleaner generic definitions.

**Feature: python-api-base-2025-state-of-art**
**Validates: Requirements 1.1, 1.2, 11.1**
**Refactored: 2025 - Split 440 lines into 3 focused modules**
"""

# Re-export pagination components
from .pagination import CursorPage, CursorPagination

# Re-export repository interface
from .repository_interface import IRepository

# Re-export in-memory implementation
from .repository_memory import InMemoryRepository

# Re-export all for public API
__all__ = [
    # Pagination
    "CursorPage",
    "CursorPagination",
    # Repository Interface
    "IRepository",
    # In-Memory Implementation
    "InMemoryRepository",
]
