"""Repository and infrastructure protocol definitions.

This module has been refactored into smaller, focused modules:
- protocols/data_access.py: Data access protocols (Repository, Cache, UnitOfWork)
- protocols/application.py: Application layer protocols (Events, CQRS, Mappers)

This file now serves as a compatibility layer, re-exporting all components.

Feature: file-size-compliance-phase2
Refactored: 2025 - Split 401 lines into 2 focused modules
"""

# Re-export data access components
from .data_access import AsyncRepository, CacheProvider, UnitOfWork

# Re-export application components
from .application import (
    Command,
    CommandHandler,
    EventHandler,
    Mapper,
    Query,
    QueryHandler,
)

# Re-export all for public API
__all__ = [
    # Data Access
    "AsyncRepository",
    "CacheProvider",
    "UnitOfWork",
    # Application Layer
    "EventHandler",
    "Command",
    "Query",
    "CommandHandler",
    "QueryHandler",
    "Mapper",
]
