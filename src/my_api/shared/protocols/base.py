"""Base protocol definitions for entity traits.

Defines fundamental protocols for common entity characteristics like
identification, timestamps, and soft deletion support.

Feature: file-size-compliance-phase2
"""

from datetime import datetime
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class Identifiable(Protocol):
    """Protocol for entities with an identifier.

    Any class with an `id` attribute satisfies this protocol.
    """

    id: Any

@runtime_checkable
class Timestamped(Protocol):
    """Protocol for entities with timestamp tracking.

    Any class with `created_at` and `updated_at` attributes satisfies this protocol.
    """

    created_at: datetime
    updated_at: datetime

@runtime_checkable
class SoftDeletable(Protocol):
    """Protocol for entities supporting soft delete.

    Any class with an `is_deleted` boolean attribute satisfies this protocol.
    """

    is_deleted: bool