"""Compatibility alias for core.base.domain.entity.

Use core.base.domain.entity directly for new code.
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

__all__ = [
    "BaseEntity",
    "AuditableEntity",
    "VersionedEntity",
    "AuditableVersionedEntity",
    "ULIDEntity",
    "AuditableULIDEntity",
    "VersionedULIDEntity",
]
