"""JWT authentication service for token generation and verification.

**Feature: core-code-review**
**Validates: Requirements 4.1, 4.4, 4.5, 11.1**
"""

from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, UTC
from typing import Any, Final, Protocol

from jose import JWTError, jwt

from my_api.core.exceptions import AuthenticationError
from my_api.shared.utils.ids import generate_ulid


class TimeSource(Protocol):
    """Protocol for injectable time sources.
    
    **Feature: core-code-review**
    **Validates: Requirements 11.1**
    """

    def now(self) -> datetime:
        """Get current UTC datetime."""
        ...


class SystemTimeSource:
    """Default system time source."""

    def now(self) -> datetime:
        """Get current UTC datetime from system clock."""
        return datetime.now(UTC)


class TokenExpiredError(AuthenticationError):
    """Raised when a token has expired."""

    def __init__(self, message: str = "Token has expired") -> None:
        super().__init__(message=message)
        self.error_code = "TOKEN_EXPIRED"


class TokenInvalidError(AuthenticationError):
    """Raised when a token is invalid or malformed."""

    def __init__(self, message: str = "Invalid token") -> None:
        super().__init__(message=message)
        self.error_code = "TOKEN_INVALID"


class TokenRevokedError(AuthenticationError):
    """Raised when a token has been revoked."""

    def __init__(self, message: str = "Token has been revoked") -> None:
        super().__init__(message=message)
        self.error_code = "TOKEN_REVOKED"


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
        """Convert payload to dictionary for JWT encoding.

        Returns:
            Dictionary representation of the payload.
        """
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
        """Create TokenPayload from dictionary.

        Args:
            data: Dictionary with payload data.

        Returns:
            TokenPayload instance.
        """
        return cls(
            sub=data["sub"],
            exp=datetime.fromtimestamp(data["exp"], tz=UTC),
            iat=datetime.fromtimestamp(data["iat"], tz=UTC),
            jti=data["jti"],
            scopes=tuple(data.get("scopes", [])),
            token_type=data.get("token_type", "access"),
        )

    def pretty_print(self) -> str:
        """Format token payload for debugging.

        Returns:
            Formatted string representation.
        """
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
    expires_in: int = 1800  # 30 minutes

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response.

        Returns:
            Dictionary representation.
        """
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "token_type": self.token_type,
            "expires_in": self.expires_in,
        }


class JWTService:
    """Service for JWT token operations.

    Handles creation, verification, and refresh of JWT tokens
    using the python-jose library.
    
    **Feature: core-code-review, core-improvements-v2**
    **Validates: Requirements 4.1, 4.4, 4.5, 11.1, 2.1, 2.2, 2.3, 2.4, 2.5**
    """

    # Default maximum number of tracked refresh tokens
    DEFAULT_MAX_TRACKED_TOKENS: Final[int] = 10000

    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 30,
        refresh_token_expire_days: int = 7,
        clock_skew_seconds: int = 30,
        time_source: TimeSource | None = None,
        max_tracked_tokens: int = DEFAULT_MAX_TRACKED_TOKENS,
    ) -> None:
        """Initialize JWT service.

        Args:
            secret_key: Secret key for signing tokens.
            algorithm: JWT signing algorithm.
            access_token_expire_minutes: Access token TTL in minutes.
            refresh_token_expire_days: Refresh token TTL in days.
            clock_skew_seconds: Allowed clock skew for expiration checks.
            time_source: Injectable time source for testing.
            max_tracked_tokens: Maximum number of refresh tokens to track for replay protection.
        """
        if not secret_key or len(secret_key) < 32:
            raise ValueError("Secret key must be at least 32 characters")

        self._secret_key = secret_key
        self._algorithm = algorithm
        self._access_expire = timedelta(minutes=access_token_expire_minutes)
        self._refresh_expire = timedelta(days=refresh_token_expire_days)
        self._clock_skew = timedelta(seconds=clock_skew_seconds)
        self._time_source = time_source or SystemTimeSource()
        self._max_tracked_tokens = max_tracked_tokens

        # Track used refresh token JTIs with expiry for bounded memory
        # OrderedDict maintains insertion order for FIFO removal
        self._used_refresh_tokens: OrderedDict[str, datetime] = OrderedDict()

    def _cleanup_expired_tokens(self) -> None:
        """Remove expired tokens from tracking.
        
        **Feature: core-improvements-v2**
        **Validates: Requirements 2.3, 2.4**
        """
        now = self._time_source.now()
        expired_jtis = [
            jti for jti, exp in self._used_refresh_tokens.items()
            if exp < now
        ]
        for jti in expired_jtis:
            del self._used_refresh_tokens[jti]

    def create_access_token(
        self,
        user_id: str,
        scopes: list[str] | None = None,
    ) -> tuple[str, TokenPayload]:
        """Create a new access token.
        
        **Feature: core-code-review, Property 6: JWT Required Claims**
        **Validates: Requirements 4.1**

        Args:
            user_id: User identifier to encode in token.
            scopes: Optional list of permission scopes.

        Returns:
            Tuple of (token_string, payload).
        """
        now = self._time_source.now()
        payload = TokenPayload(
            sub=user_id,
            exp=now + self._access_expire,
            iat=now,
            jti=generate_ulid(),
            scopes=tuple(scopes or []),
            token_type="access",
        )

        token = jwt.encode(
            payload.to_dict(),
            self._secret_key,
            algorithm=self._algorithm,
        )

        return token, payload

    def create_refresh_token(self, user_id: str) -> tuple[str, TokenPayload]:
        """Create a new refresh token.

        Args:
            user_id: User identifier to encode in token.

        Returns:
            Tuple of (token_string, payload).
        """
        now = self._time_source.now()
        payload = TokenPayload(
            sub=user_id,
            exp=now + self._refresh_expire,
            iat=now,
            jti=generate_ulid(),
            scopes=(),
            token_type="refresh",
        )

        token = jwt.encode(
            payload.to_dict(),
            self._secret_key,
            algorithm=self._algorithm,
        )

        return token, payload

    def create_token_pair(
        self,
        user_id: str,
        scopes: list[str] | None = None,
    ) -> tuple[TokenPair, TokenPayload, TokenPayload]:
        """Create both access and refresh tokens.

        Args:
            user_id: User identifier.
            scopes: Optional permission scopes for access token.

        Returns:
            Tuple of (TokenPair, access_payload, refresh_payload).
        """
        access_token, access_payload = self.create_access_token(user_id, scopes)
        refresh_token, refresh_payload = self.create_refresh_token(user_id)

        pair = TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=int(self._access_expire.total_seconds()),
        )

        return pair, access_payload, refresh_payload

    def verify_token(
        self,
        token: str,
        expected_type: str | None = None,
    ) -> TokenPayload:
        """Verify and decode a JWT token.
        
        **Feature: core-code-review**
        **Validates: Requirements 4.4**

        Args:
            token: JWT token string to verify.
            expected_type: Expected token type (access/refresh).

        Returns:
            Decoded TokenPayload.

        Raises:
            TokenExpiredError: If token has expired.
            TokenInvalidError: If token is invalid or malformed.
        """
        try:
            data = jwt.decode(
                token,
                self._secret_key,
                algorithms=[self._algorithm],
                options={"leeway": self._clock_skew.total_seconds()},
            )
        except JWTError as e:
            error_msg = str(e).lower()
            if "expired" in error_msg:
                raise TokenExpiredError() from e
            raise TokenInvalidError(f"Token verification failed: {e}") from e

        payload = TokenPayload.from_dict(data)

        # Check expiration with clock skew tolerance
        now = self._time_source.now()
        if payload.exp < (now - self._clock_skew):
            raise TokenExpiredError()

        # Validate token type if specified
        if expected_type and payload.token_type != expected_type:
            raise TokenInvalidError(
                f"Expected {expected_type} token, got {payload.token_type}"
            )

        return payload

    def verify_refresh_token(self, token: str) -> TokenPayload:
        """Verify refresh token with replay protection and memory management.
        
        **Feature: core-code-review, core-improvements-v2**
        **Validates: Requirements 4.5, 2.1, 2.2, 2.3, 2.4**

        Args:
            token: Refresh token string.

        Returns:
            Decoded TokenPayload.

        Raises:
            TokenRevokedError: If token has already been used.
            TokenExpiredError: If token has expired.
            TokenInvalidError: If token is invalid.
        """
        # Cleanup expired tokens first
        self._cleanup_expired_tokens()

        payload = self.verify_token(token, expected_type="refresh")

        # Check for replay attack
        if payload.jti in self._used_refresh_tokens:
            raise TokenRevokedError("Refresh token has already been used")

        # Track with expiry for cleanup
        self._used_refresh_tokens[payload.jti] = payload.exp

        # Enforce max size (FIFO removal of oldest)
        while len(self._used_refresh_tokens) > self._max_tracked_tokens:
            self._used_refresh_tokens.popitem(last=False)

        return payload

    def clear_used_refresh_tokens(self) -> None:
        """Clear used refresh token tracking (for testing)."""
        self._used_refresh_tokens.clear()

    def decode_token_unverified(self, token: str) -> TokenPayload:
        """Decode token without verification (for debugging).

        Args:
            token: JWT token string.

        Returns:
            Decoded TokenPayload.

        Raises:
            TokenInvalidError: If token cannot be decoded.
        """
        try:
            data = jwt.decode(
                token,
                self._secret_key,
                algorithms=[self._algorithm],
                options={"verify_exp": False},
            )
            return TokenPayload.from_dict(data)
        except JWTError as e:
            raise TokenInvalidError(f"Cannot decode token: {e}") from e
