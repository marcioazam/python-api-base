"""Repository and infrastructure protocol definitions.

This module has been refactored into smaller, focused modules:
- protocols/data_access.py: Data access protocols (Repository, Cache, UnitOfWork)
- protocols/application.py: Application layer protocols (Events, CQRS, Mappers)

This file now serves as a compatibility layer, re-exporting all components.

Feature: file-size-compliance-phase2
Refactored: 2025 - Split 401 lines into 2 focused modules
"""

# Re-export data access components
# Re-export application components
from core.protocols.application import (
    Command,
    CommandHandler,
    EventHandler,
    Mapper,
    Query,
    QueryHandler,
)
from core.protocols.data_access import AsyncRepository, CacheProvider, UnitOfWork

# Re-export all for public API
__all__ = [
    # Data Access
    "AsyncRepository",
    "CacheProvider",
    "Command",
    "CommandHandler",
    # Application Layer
    "EventHandler",
    "Mapper",
    "Query",
    "QueryHandler",
    "UnitOfWork",
]
