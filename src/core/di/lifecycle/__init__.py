"""Service lifecycle management.

Contains Lifetime enum and Registration dataclass for managing service lifecycles.

**Feature: core-di-restructuring-2025**
"""

from core.di.lifecycle.lifecycle import Lifetime, Registration

__all__ = [
    "Lifetime",
    "Registration",
]
