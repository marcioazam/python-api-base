"""CQRS Handler base classes.

Provides abstract base classes for command and query handlers.

**Feature: architecture-restructuring-2025**
"""

from application.common.cqrs.handlers.handlers import CommandHandler, QueryHandler

__all__ = [
    "CommandHandler",
    "QueryHandler",
]
