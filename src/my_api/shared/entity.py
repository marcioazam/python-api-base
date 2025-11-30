"""Base entity with generic ID type and common fields.

Uses PEP 695 type parameter syntax (Python 3.12+) for cleaner generic definitions.
"""

from datetime import datetime, UTC

from pydantic import BaseModel, Field

from my_api.shared.utils.ids import generate_ulid


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


class ULIDEntity(BaseEntity[str]):
    """Base entity with ULID as the ID type.

    Automatically generates a ULID for new entities if no ID is provided.
    """

    id: str | None = Field(
        default_factory=generate_ulid,
        description="ULID identifier",
    )
