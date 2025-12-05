"""Dependency resolution and error handling.

Contains resolver logic and DI-specific exceptions.

**Feature: core-di-restructuring-2025**
"""

from core.di.resolution.exceptions import (
    CircularDependencyError,
    DependencyResolutionError,
    InvalidFactoryError,
    ServiceNotRegisteredError,
)
from core.di.resolution.resolver import Resolver

__all__ = [
    "CircularDependencyError",
    "DependencyResolutionError",
    "InvalidFactoryError",
    "Resolver",
    "ServiceNotRegisteredError",
]
