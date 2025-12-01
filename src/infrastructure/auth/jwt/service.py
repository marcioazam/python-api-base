"""JWT service implementation.

**Feature: full-codebase-review-2025, Task 1.3: Refactor jwt.py**
**Validates: Requirements 9.2**
"""

from collections import OrderedDict
from datetime import datetime, timedelta
from typing import Final

from jose import JWTError, jwt

from core.shared.utils.ids import generate_ulid

from .errors import TokenExpiredError, TokenInvalidError, TokenRevokedError
from .models import TokenPair, TokenPayload
from .time_source import SystemTimeSource, TimeSource


class JWTService:
    """Service for JWT token operations.

    **Feature: core-code-review, core-improvements-v2**
    **Validates: Requirements 4.1, 4.4, 4.5, 11.1, 2.1, 2.2, 2.3, 2.4, 2.5**
    """

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
        """Initialize JWT service."""
        if not secret_key or len(secret_key) < 32:
            raise ValueError("Secret key must be at least 32 characters")

        self._secret_key = secret_key
        self._algorithm = algorithm
        self._access_expire = timedelta(minutes=access_token_expire_minutes)
        self._refresh_expire = timedelta(days=refresh_token_expire_days)
        self._clock_skew = timedelta(seconds=clock_skew_seconds)
        self._time_source = time_source or SystemTimeSource()
        self._max_tracked_tokens = max_tracked_tokens
        self._used_refresh_tokens: OrderedDict[str, datetime] = OrderedDict()

    def _cleanup_expired_tokens(self) -> None:
        """Remove expired tokens from tracking."""
        now = self._time_source.now()
        expired_jtis = [
            jti for jti, exp in self._used_refresh_tokens.items() if exp < now
        ]
        for jti in expired_jtis:
            del self._used_refresh_tokens[jti]

    def create_access_token(
        self, user_id: str, scopes: list[str] | None = None
    ) -> tuple[str, TokenPayload]:
        """Create a new access token.

        **Feature: core-code-review, Property 6: JWT Required Claims**
        **Validates: Requirements 4.1**
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
            payload.to_dict(), self._secret_key, algorithm=self._algorithm
        )
        return token, payload

    def create_refresh_token(self, user_id: str) -> tuple[str, TokenPayload]:
        """Create a new refresh token."""
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
            payload.to_dict(), self._secret_key, algorithm=self._algorithm
        )
        return token, payload

    def create_token_pair(
        self, user_id: str, scopes: list[str] | None = None
    ) -> tuple[TokenPair, TokenPayload, TokenPayload]:
        """Create both access and refresh tokens."""
        access_token, access_payload = self.create_access_token(user_id, scopes)
        refresh_token, refresh_payload = self.create_refresh_token(user_id)
        pair = TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=int(self._access_expire.total_seconds()),
        )
        return pair, access_payload, refresh_payload

    def verify_token(
        self, token: str, expected_type: str | None = None
    ) -> TokenPayload:
        """Verify and decode a JWT token.

        **Feature: core-code-review**
        **Validates: Requirements 4.4**
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
        now = self._time_source.now()
        if payload.exp < (now - self._clock_skew):
            raise TokenExpiredError()
        if expected_type and payload.token_type != expected_type:
            raise TokenInvalidError(
                f"Expected {expected_type} token, got {payload.token_type}"
            )
        return payload

    def verify_refresh_token(self, token: str) -> TokenPayload:
        """Verify refresh token with replay protection.

        **Feature: core-code-review, core-improvements-v2**
        **Validates: Requirements 4.5, 2.1, 2.2, 2.3, 2.4**
        """
        self._cleanup_expired_tokens()
        payload = self.verify_token(token, expected_type="refresh")
        if payload.jti in self._used_refresh_tokens:
            raise TokenRevokedError("Refresh token has already been used")
        self._used_refresh_tokens[payload.jti] = payload.exp
        while len(self._used_refresh_tokens) > self._max_tracked_tokens:
            self._used_refresh_tokens.popitem(last=False)
        return payload

    def clear_used_refresh_tokens(self) -> None:
        """Clear used refresh token tracking (for testing)."""
        self._used_refresh_tokens.clear()

    def decode_token_unverified(self, token: str) -> TokenPayload:
        """Decode token without verification (for debugging)."""
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
