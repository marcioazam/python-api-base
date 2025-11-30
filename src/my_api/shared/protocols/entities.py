"""Entity protocol compositions for domain modeling.

Provides composite protocols that combine base traits for common
entity patterns like tracked entities, deletable entities, and
versioned entities.

Feature: file-size-compliance-phase2
"""

from typing import Protocol, runtime_checkable
from .base import Identifiable, Timestamped, SoftDeletable


@runtime_checkable
class Entity(Identifiable, Protocol):
    """Protocol for basic entities with an identifier.

    Combines: Identifiable
    Use this as a bound for TypeVars when you need entities with IDs.

    Example:
        T = TypeVar("T", bound=Entity)
    """

    pass

@runtime_checkable
class TrackedEntity(Identifiable, Timestamped, Protocol):
    """Protocol for entities with ID and timestamp tracking.

    Combines: Identifiable + Timestamped
    Use this as a bound for TypeVars when you need entities with
    both ID and timestamp fields.

    Example:
        T = TypeVar("T", bound=TrackedEntity)

        class MyRepository(Generic[T]):
            async def get_recent(self, since: datetime) -> list[T]:
                # T is guaranteed to have id, created_at, updated_at
                ...
    """

    pass

@runtime_checkable
class DeletableEntity(Identifiable, SoftDeletable, Protocol):
    """Protocol for entities with ID and soft delete support.

    Combines: Identifiable + SoftDeletable
    Use this as a bound for TypeVars when you need entities that
    support soft deletion.

    Example:
        T = TypeVar("T", bound=DeletableEntity)
    """

    pass

@runtime_checkable
class FullEntity(Identifiable, Timestamped, SoftDeletable, Protocol):
    """Protocol for entities with all common fields.

    Combines: Identifiable + Timestamped + SoftDeletable
    Use this as a bound for TypeVars when you need entities with
    ID, timestamps, and soft delete support.

    Example:
        T = TypeVar("T", bound=FullEntity)

        class BaseRepository(Generic[T]):
            async def get_active(self) -> list[T]:
                # T is guaranteed to have id, created_at, updated_at, is_deleted
                return [e for e in self._storage if not e.is_deleted]
    """

    pass

@runtime_checkable
class Auditable(Identifiable, Timestamped, Protocol):
    """Protocol for auditable entities.

    Combines: Identifiable + Timestamped
    Alias for TrackedEntity, semantically indicates audit trail support.
    """

    pass

@runtime_checkable
class Versionable(Protocol):
    """Protocol for entities with optimistic locking.

    Entities implementing this protocol support version-based
    concurrency control.
    """

    version: int

@runtime_checkable
class VersionedEntity(Identifiable, Timestamped, Versionable, Protocol):
    """Protocol for entities with versioning support.

    Combines: Identifiable + Timestamped + Versionable
    Use this for entities that need optimistic locking.

    Example:
        T = TypeVar("T", bound=VersionedEntity)

        async def update_with_lock(entity: T, new_version: int) -> T:
            if entity.version != new_version - 1:
                raise ConcurrencyError("Version mismatch")
            ...
    """

    pass