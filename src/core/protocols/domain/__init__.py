"""Domain entity protocols.

Defines protocols for domain entities with various traits and capabilities.

**Feature: core-protocols-restructuring-2025**
"""

from core.protocols.domain.entities import (
    Auditable,
    DeletableEntity,
    Entity,
    FullEntity,
    TrackedEntity,
    Versionable,
    VersionedEntity,
)

__all__ = [
    "Auditable",
    "DeletableEntity",
    "Entity",
    "FullEntity",
    "TrackedEntity",
    "Versionable",
    "VersionedEntity",
]
