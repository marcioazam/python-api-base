"""CQRS base classes.

**Feature: architecture-restructuring-2025**
"""

from core.base.cqrs.command import BaseCommand
from core.base.cqrs.query import BaseQuery

__all__ = [
    "BaseCommand",
    "BaseQuery",
]
