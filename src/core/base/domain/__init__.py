"""Domain building blocks.

Provides DDD tactical patterns:
- Entity: Base entity with identity
- AggregateRoot: Aggregate boundary with events
- ValueObject: Immutable value types
"""

from core.base.domain.entity import (
    BaseEntity,
    AuditableEntity,
    VersionedEntity,
    AuditableVersionedEntity,
    ULIDEntity,
    AuditableULIDEntity,
    VersionedULIDEntity,
)
from core.base.domain.aggregate_root import AggregateRoot
from core.base.domain.value_object import BaseValueObject

__all__ = [
    # Entity
    "BaseEntity",
    "AuditableEntity",
    "VersionedEntity",
    "AuditableVersionedEntity",
    "ULIDEntity",
    "AuditableULIDEntity",
    "VersionedULIDEntity",
    # Aggregate
    "AggregateRoot",
    # Value Object
    "BaseValueObject",
]
