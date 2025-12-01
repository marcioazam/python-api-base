"""Base Query class for CQRS pattern.

Queries represent requests for data without side effects.

**Feature: architecture-restructuring-2025, ultimate-generics-code-review-2025**
**Validates: Requirements 3.2, 1.1**
"""

from abc import ABC
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

try:
    from core.shared.utils.time import utc_now
except ImportError:

    def utc_now() -> datetime:
        return datetime.now(UTC)


@dataclass(frozen=True)
class BaseQuery[TResult](ABC):
    """Base class for all queries in CQRS pattern.

    Queries are immutable objects that represent a request for data.
    They should:
    - Be named with interrogative style (GetUser, ListOrders)
    - Not modify system state
    - Be cacheable when appropriate

    Type Parameters:
        TResult: The expected return type of the query.

    Attributes:
        query_id: Unique identifier for the query.
        timestamp: When the query was created.
        correlation_id: ID for tracing related operations.
        cache_key: Optional key for caching results.
    """

    query_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=utc_now)
    correlation_id: str | None = None
    cache_key: str | None = None
    cache_ttl: int | None = None  # TTL in seconds

    @property
    def query_type(self) -> str:
        """Return the query type identifier."""
        return self.__class__.__name__

    def get_cache_key(self) -> str:
        """Generate cache key for this query.

        Override in subclasses for custom cache key generation.

        Returns:
            Cache key string.
        """
        if self.cache_key:
            return self.cache_key
        return f"{self.query_type}:{self.query_id}"

    def to_dict(self) -> dict[str, Any]:
        """Serialize query to dictionary.

        Returns:
            Dictionary representation of the query.
        """
        from dataclasses import asdict

        return asdict(self)
