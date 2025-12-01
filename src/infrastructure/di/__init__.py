"""Infrastructure DI module - Application container configuration.

**Feature: architecture-restructuring-2025**
"""

from .app_container import (
    Container,
    LifecycleHookError,
    LifecycleManager,
    create_container,
    lifecycle,
)

__all__ = [
    "Container",
    "LifecycleHookError",
    "LifecycleManager",
    "create_container",
    "lifecycle",
]
