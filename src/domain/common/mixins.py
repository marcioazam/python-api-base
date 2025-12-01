"""Domain entity mixins for common functionality.

Provides reusable mixins for timestamps, soft delete, and audit fields.
Uses PEP 695 type parameter syntax (Python 3.12+).
"""

from dataclasses import dataclass, field
from datetime import datetime, UTC


@dataclass
class TimestampMixin:
    """Mixin for timestamp fields.

    Provides created_at and updated_at fields with automatic
    timestamp management.
    """

    created_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    updated_at: datetime | None = None

    def touch(self) -> None:
        """Update the updated_at timestamp to current time."""
        object.__setattr__(self, "updated_at", datetime.now(tz=UTC))


@dataclass
class SoftDeleteMixin:
    """Mixin for soft delete functionality.

    Provides is_deleted flag and deleted_at timestamp with
    methods for soft deletion and restoration.
    """

    is_deleted: bool = False
    deleted_at: datetime | None = None

    def soft_delete(self) -> None:
        """Mark entity as soft deleted."""
        object.__setattr__(self, "is_deleted", True)
        object.__setattr__(self, "deleted_at", datetime.now(tz=UTC))

    def restore(self) -> None:
        """Restore a soft-deleted entity."""
        object.__setattr__(self, "is_deleted", False)
        object.__setattr__(self, "deleted_at", None)


@dataclass
class AuditableMixin:
    """Mixin for audit fields.

    Tracks who created and last updated the entity.
    """

    created_by: str | None = None
    updated_by: str | None = None

    def set_creator(self, user_id: str) -> None:
        """Set the creator user ID."""
        object.__setattr__(self, "created_by", user_id)

    def set_updater(self, user_id: str) -> None:
        """Set the updater user ID."""
        object.__setattr__(self, "updated_by", user_id)


@dataclass
class VersionedMixin:
    """Mixin for optimistic concurrency control.

    Provides version field for detecting concurrent modifications.
    """

    version: int = 1

    def increment_version(self) -> None:
        """Increment the version number."""
        object.__setattr__(self, "version", self.version + 1)


@dataclass
class TenantMixin:
    """Mixin for multi-tenancy support.

    Provides tenant_id field for row-level tenant isolation.
    """

    tenant_id: str | None = None

    def set_tenant(self, tenant_id: str) -> None:
        """Set the tenant ID."""
        object.__setattr__(self, "tenant_id", tenant_id)
