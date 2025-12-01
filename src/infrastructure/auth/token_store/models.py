"""Token store data models.

Feature: file-size-compliance-phase2
Validates: Requirements 3.1, 5.1, 5.2, 5.3
"""

from dataclasses import dataclass
from datetime import datetime, UTC
from typing import Any


@dataclass(frozen=True, slots=True)
class StoredToken:
    """Stored refresh token data."""

    jti: str
    user_id: str
    created_at: datetime
    expires_at: datetime
    revoked: bool = False

    def is_expired(self) -> bool:
        """Check if token has expired."""
        return datetime.now(UTC) > self.expires_at

    def is_valid(self) -> bool:
        """Check if token is valid (not expired and not revoked)."""
        return not self.revoked and not self.is_expired()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "jti": self.jti,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "revoked": self.revoked,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StoredToken":
        """Create from dictionary."""
        return cls(
            jti=data["jti"],
            user_id=data["user_id"],
            created_at=datetime.fromisoformat(data["created_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"]),
            revoked=data.get("revoked", False),
        )
