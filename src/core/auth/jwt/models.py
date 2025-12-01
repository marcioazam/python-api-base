"""JWT token models.

**Feature: full-codebase-review-2025, Task 1.3: Refactor jwt.py**
**Validates: Requirements 9.2**
"""

from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any


@dataclass(frozen=True, slots=True)
class TokenPayload:
    """JWT token payload data.

    Attributes:
        sub: Subject (user_id).
        exp: Expiration timestamp.
        iat: Issued at timestamp.
        jti: JWT ID for revocation tracking.
        scopes: List of permission scopes.
        token_type: Type of token (access or refresh).
    """

    sub: str
    exp: datetime
    iat: datetime
    jti: str
    scopes: tuple[str, ...] = field(default_factory=tuple)
    token_type: str = "access"

    def to_dict(self) -> dict[str, Any]:
        """Convert payload to dictionary for JWT encoding."""
        return {
            "sub": self.sub,
            "exp": int(self.exp.timestamp()),
            "iat": int(self.iat.timestamp()),
            "jti": self.jti,
            "scopes": list(self.scopes),
            "token_type": self.token_type,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TokenPayload":
        """Create TokenPayload from dictionary."""
        return cls(
            sub=data["sub"],
            exp=datetime.fromtimestamp(data["exp"], tz=UTC),
            iat=datetime.fromtimestamp(data["iat"], tz=UTC),
            jti=data["jti"],
            scopes=tuple(data.get("scopes", [])),
            token_type=data.get("token_type", "access"),
        )

    def pretty_print(self) -> str:
        """Format token payload for debugging."""
        lines = [
            "TokenPayload {",
            f"  sub: {self.sub}",
            f"  exp: {self.exp.isoformat()}",
            f"  iat: {self.iat.isoformat()}",
            f"  jti: {self.jti}",
            f"  scopes: {list(self.scopes)}",
            f"  token_type: {self.token_type}",
            "}",
        ]
        return "\n".join(lines)


@dataclass(frozen=True, slots=True)
class TokenPair:
    """Access and refresh token pair.

    Attributes:
        access_token: JWT access token string.
        refresh_token: JWT refresh token string.
        token_type: Token type for Authorization header.
        expires_in: Access token expiration in seconds.
    """

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 1800

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "token_type": self.token_type,
            "expires_in": self.expires_in,
        }
