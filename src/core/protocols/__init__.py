"""Protocol definitions for the application.

Organized into subpackages by responsibility:
- entity/: Base entity trait protocols
- application/: Application patterns (CQRS, event handlers, mappers)
- data_access/: Data access patterns (repositories, caches, UoW)
- domain/: Domain entity protocols

Feature: file-size-compliance-phase2
"""

from core.protocols.entity import Identifiable, SoftDeletable, Timestamped
from core.protocols.domain import (
    Auditable,
    DeletableEntity,
    Entity,
    FullEntity,
    TrackedEntity,
    Versionable,
    VersionedEntity,
)
from core.protocols.application import (
    Command,
    CommandHandler,
    EventHandler,
    Mapper,
    Query,
    QueryHandler,
)
from core.protocols.data_access import (
    AsyncRepository,
    CacheProvider,
    UnitOfWork,
)

__all__ = [
    "AsyncRepository",
    "Auditable",
    "CacheProvider",
    "Command",
    "CommandHandler",
    "DeletableEntity",
    "Entity",
    "EventHandler",
    "FullEntity",
    "Identifiable",
    "Mapper",
    "Query",
    "QueryHandler",
    "SoftDeletable",
    "Timestamped",
    "TrackedEntity",
    "UnitOfWork",
    "Versionable",
    "VersionedEntity",
]
