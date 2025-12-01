"""Token store protocols and base classes.

Feature: file-size-compliance-phase2
Validates: Requirements 3.1, 5.1, 5.2, 5.3
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Protocol, runtime_checkable

from .models import StoredToken


@runtime_checkable
class TokenStoreProtocol(Protocol):
    """Protocol for token storage implementations."""

    async def store(self, jti: str, user_id: str, expires_at: datetime) -> None: ...
    async def get(self, jti: str) -> StoredToken | None: ...
    async def revoke(self, jti: str) -> bool: ...
    async def revoke_all_for_user(self, user_id: str) -> int: ...
    async def is_valid(self, jti: str) -> bool: ...
    async def cleanup_expired(self) -> int: ...


class RefreshTokenStore(ABC):
    """Abstract base class for refresh token storage."""

    @abstractmethod
    async def store(self, jti: str, user_id: str, expires_at: datetime) -> None: ...

    @abstractmethod
    async def get(self, jti: str) -> StoredToken | None: ...

    @abstractmethod
    async def revoke(self, jti: str) -> bool: ...

    @abstractmethod
    async def revoke_all_for_user(self, user_id: str) -> int: ...

    @abstractmethod
    async def is_valid(self, jti: str) -> bool: ...

    @abstractmethod
    async def cleanup_expired(self) -> int: ...
