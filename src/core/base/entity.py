"""Base entity with generic ID type and common fields.

Uses PEP 695 type parameter syntax (Python 3.12+) for cleaner generic definitions.

**Feature: python-api-base-2025-state-of-art**
**Validates: Requirements 11.1, 11.2**
"""

from datetime import datetime, UTC

from pydantic import BaseModel, Field

from core.shared.utils.ids import generate_ulid


class BaseEntity[IdType: (str, int)](BaseModel):
    """Base entity with common fields for all domain entities.

    Provides standard fields for identity, timestamps, and soft delete
    that are common across all domain entities.

    Type Parameters:
        IdType: The type of the entity ID (str or int).
    """

    id: IdType | None = Field(default=None, description="Unique entity identifier")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC),
        description="Timestamp when entity was created",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC),
        description="Timestamp when entity was last updated",
    )
    is_deleted: bool = Field(
        default=False,
        description="Soft delete flag",
    )

    model_config = {"from_attributes": True}

    def mark_updated(self) -> None:
        """Update the updated_at timestamp to current time."""
        object.__setattr__(self, "updated_at", datetime.now(tz=UTC))

    def mark_deleted(self) -> None:
        """Mark entity as soft deleted."""
        object.__setattr__(self, "is_deleted", True)
        self.mark_updated()

    def mark_restored(self) -> None:
        """Restore soft-deleted entity."""
        object.__setattr__(self, "is_deleted", False)
        self.mark_updated()


class AuditableEntity[IdType: (str, int)](BaseEntity[IdType]):
    """Entity with audit trail fields.

    Extends BaseEntity with created_by and updated_by fields
    for tracking who made changes.

    Type Parameters:
        IdType: The type of the entity ID (str or int).

    **Feature: python-api-base-2025-state-of-art**
    **Validates: Requirements 11.1, 11.2**
    """

    created_by: str | None = Field(
        default=None,
        description="ID of user who created this entity",
    )
    updated_by: str | None = Field(
        default=None,
        description="ID of user who last updated this entity",
    )

    def mark_updated_by(self, user_id: str) -> None:
        """Update timestamp and user who made the change."""
        object.__setattr__(self, "updated_by", user_id)
        self.mark_updated()


class VersionedEntity[IdType: (str, int), VersionT: (int, str) = int](
    BaseEntity[IdType]
):
    """Entity with optimistic locking version.

    Extends BaseEntity with a version field for optimistic concurrency control.

    Type Parameters:
        IdType: The type of the entity ID (str or int).
        VersionT: The type of the version (int or str), defaults to int.

    **Feature: python-api-base-2025-state-of-art**
    **Validates: Requirements 11.1**
    """

    version: VersionT = Field(
        default=1,  # type: ignore
        description="Version number for optimistic locking",
    )

    def increment_version(self) -> None:
        """Increment version number."""
        current = self.version
        if isinstance(current, int):
            object.__setattr__(self, "version", current + 1)
        else:
            # For string versions, append increment
            object.__setattr__(self, "version", f"{current}.1")
        self.mark_updated()


class AuditableVersionedEntity[IdType: (str, int), VersionT: (int, str) = int](
    AuditableEntity[IdType]
):
    """Entity with both audit trail and optimistic locking.

    Combines AuditableEntity and VersionedEntity features.

    Type Parameters:
        IdType: The type of the entity ID (str or int).
        VersionT: The type of the version (int or str), defaults to int.
    """

    version: VersionT = Field(
        default=1,  # type: ignore
        description="Version number for optimistic locking",
    )

    def increment_version(self) -> None:
        """Increment version number."""
        current = self.version
        if isinstance(current, int):
            object.__setattr__(self, "version", current + 1)
        else:
            object.__setattr__(self, "version", f"{current}.1")
        self.mark_updated()

    def mark_updated_by_with_version(self, user_id: str) -> None:
        """Update timestamp, user, and increment version."""
        object.__setattr__(self, "updated_by", user_id)
        self.increment_version()


class ULIDEntity(BaseEntity[str]):
    """Base entity with ULID as the ID type.

    Automatically generates a ULID for new entities if no ID is provided.
    """

    id: str | None = Field(
        default_factory=generate_ulid,
        description="ULID identifier",
    )


class AuditableULIDEntity(AuditableEntity[str]):
    """Auditable entity with ULID as the ID type.

    Automatically generates a ULID for new entities if no ID is provided.
    """

    id: str | None = Field(
        default_factory=generate_ulid,
        description="ULID identifier",
    )


class VersionedULIDEntity(VersionedEntity[str, int]):
    """Versioned entity with ULID as the ID type.

    Automatically generates a ULID for new entities if no ID is provided.
    """

    id: str | None = Field(
        default_factory=generate_ulid,
        description="ULID identifier",
    )
