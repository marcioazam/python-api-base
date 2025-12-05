"""Container management for dependency injection.

Contains the main Container class and Scope for managing dependencies.

**Feature: core-di-restructuring-2025**
"""

from core.di.container.container import Container
from core.di.container.scopes import Scope

__all__ = [
    "Container",
    "Scope",
]
