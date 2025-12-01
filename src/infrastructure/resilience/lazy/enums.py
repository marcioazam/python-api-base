"""Lazy loading enums.

**Feature: file-size-compliance-phase2, Task 2.5**
**Validates: Requirements 1.5, 5.1, 5.2, 5.3**
"""

from enum import Enum, auto


class LoadState(Enum):
    """State of a lazy-loaded value."""

    NOT_LOADED = auto()
    LOADING = auto()
    LOADED = auto()
    ERROR = auto()
