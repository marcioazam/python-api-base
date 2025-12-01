"""API Key models and data classes.

**Feature: full-codebase-review-2025, Task 1.2: Refactor api_key_service**
**Validates: Requirements 9.2**
"""

from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any

from .enums import KeyScope, KeyStatus


@dataclass
class APIKey:
    """API key entity."""

    key_id: str
    key_hash: str
    client_id: str
    name: str
    scopes: list[KeyScope] = field(default_factory=list)
    status: KeyStatus = KeyStatus.ACTIVE
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime | None = None
    last_used_at: datetime | None = None
    rate_limit: int = 1000
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        """Check if key is expired."""
        if self.expires_at is None:
            return False
        return datetime.now(UTC) > self.expires_at

    @property
    def is_active(self) -> bool:
        """Check if key is active and not expired."""
        return self.status == KeyStatus.ACTIVE and not self.is_expired

    def has_scope(self, scope: KeyScope) -> bool:
        """Check if key has a specific scope."""
        if KeyScope.FULL in self.scopes:
            return True
        if KeyScope.ADMIN in self.scopes and scope in [KeyScope.READ, KeyScope.WRITE]:
            return True
        return scope in self.scopes


@dataclass
class KeyValidationResult:
    """Result of API key validation."""

    valid: bool
    key: APIKey | None = None
    error: str | None = None
    remaining_requests: int | None = None


@dataclass
class KeyRotationResult:
    """Result of key rotation."""

    success: bool
    old_key_id: str | None = None
    new_key: str | None = None
    new_key_id: str | None = None
    error: str | None = None
