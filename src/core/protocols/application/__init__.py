"""Application layer protocols.

Defines protocols for application patterns including event handlers,
CQRS commands/queries, and entity mappers.

**Feature: core-protocols-restructuring-2025**
"""

from core.protocols.application.application import (
    Command,
    CommandHandler,
    EventHandler,
    Mapper,
    Query,
    QueryHandler,
)

__all__ = [
    "Command",
    "CommandHandler",
    "EventHandler",
    "Mapper",
    "Query",
    "QueryHandler",
]
