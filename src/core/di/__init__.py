"""Dependency Injection module.

This module provides a type-safe dependency injection container with:
- Auto-wiring of constructor dependencies
- Lifetime management (TRANSIENT, SINGLETON, SCOPED)
- Circular dependency detection
- PEP 695 generics support

**Feature: generics-100-percent-fixes**
**Validates: Requirements 28.1, 28.2, 28.3, 4.1, 4.2, 4.3, 4.4, 4.5**

Example:
    >>> from core.di import Container, Lifetime
    >>> container = Container()
    >>> container.register(Database, lifetime=Lifetime.SINGLETON)
    >>> container.register(UserService)
    >>> service = container.resolve(UserService)
"""

from .container import Container, Scope
from .exceptions import (
    CircularDependencyError,
    DependencyResolutionError,
    InvalidFactoryError,
    ServiceNotRegisteredError,
)
from .lifecycle import Lifetime, Registration

__all__ = [
    # Container
    "Container",
    "Scope",
    # Lifecycle
    "Lifetime",
    "Registration",
    # Exceptions
    "DependencyResolutionError",
    "CircularDependencyError",
    "InvalidFactoryError",
    "ServiceNotRegisteredError",
]
