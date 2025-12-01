"""JWT protocols and base classes.

**Feature: api-base-score-100**
**Validates: Requirements 1.2, 1.3**
"""

import logging
from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol, runtime_checkable

from jose import JWTError, jwt

from .exceptions import AlgorithmMismatchError, InvalidKeyError

logger = logging.getLogger(__name__)


@runtime_checkable
class JWTAlgorithmProvider(Protocol):
    """Protocol for JWT algorithm providers.

    **Feature: api-base-score-100, Property 1: RS256 Sign-Verify Round Trip**
    **Validates: Requirements 1.2**

    Example:
        >>> provider: JWTAlgorithmProvider = RS256Provider(...)
        >>> token = provider.sign({"sub": "user123"})
        >>> claims = provider.verify(token)
    """

    @property
    def algorithm(self) -> str:
        """Get the algorithm name (RS256, ES256, HS256)."""
        ...

    def sign(
        self, payload: dict[str, Any], expires_delta: timedelta | None = None
    ) -> str:
        """Sign a payload and return JWT token.

        Args:
            payload: Claims to include in token.
            expires_delta: Token expiration time (overrides default).

        Returns:
            Signed JWT token string.

        Raises:
            InvalidKeyError: If signing fails.
        """
        ...

    def verify(self, token: str) -> dict[str, Any]:
        """Verify a JWT token and return claims.

        Args:
            token: JWT token string to verify.

        Returns:
            Decoded claims dictionary.

        Raises:
            AlgorithmMismatchError: If token algorithm doesn't match.
            InvalidKeyError: If verification fails.
        """
        ...


class BaseJWTProvider(ABC):
    """Base class for JWT providers with common functionality.

    Provides shared implementation for token signing and verification,
    handling standard claims (iat, exp, iss, aud) automatically.

    **Feature: api-base-score-100**
    **Validates: Requirements 1.2, 1.3**
    """

    def __init__(
        self,
        issuer: str | None = None,
        audience: str | None = None,
        default_expiry: timedelta = timedelta(hours=1),
    ) -> None:
        """Initialize base JWT provider.

        Args:
            issuer: Token issuer claim (iss). Optional.
            audience: Token audience claim (aud). Optional.
            default_expiry: Default token expiration time. Default: 1 hour.
        """
        self._issuer = issuer
        self._audience = audience
        self._default_expiry = default_expiry

    @property
    @abstractmethod
    def algorithm(self) -> str:
        """Get the algorithm name.

        Returns:
            Algorithm identifier (RS256, ES256, HS256).
        """
        ...

    @abstractmethod
    def _get_signing_key(self) -> str:
        """Get key for signing.

        Returns:
            Signing key (private key or secret).

        Raises:
            InvalidKeyError: If signing key is not available.
        """
        ...

    @abstractmethod
    def _get_verification_key(self) -> str:
        """Get key for verification.

        Returns:
            Verification key (public key or secret).

        Raises:
            InvalidKeyError: If verification key is not available.
        """
        ...

    def sign(
        self, payload: dict[str, Any], expires_delta: timedelta | None = None
    ) -> str:
        """Sign a payload and return JWT token.

        Automatically adds standard claims:
        - iat (issued at): Current timestamp
        - exp (expiration): Current timestamp + expires_delta
        - iss (issuer): If configured
        - aud (audience): If configured

        **Feature: api-base-score-100, Property 1: RS256 Sign-Verify Round Trip**
        **Validates: Requirements 1.2**

        Args:
            payload: Custom claims to include in token.
            expires_delta: Token expiration time (overrides default).

        Returns:
            Signed JWT token string.

        Raises:
            InvalidKeyError: If signing fails.
        """
        now = datetime.now(UTC)
        expiry = expires_delta or self._default_expiry

        claims = {
            **payload,
            "iat": now,
            "exp": now + expiry,
        }

        if self._issuer:
            claims["iss"] = self._issuer
        if self._audience:
            claims["aud"] = self._audience

        try:
            return jwt.encode(claims, self._get_signing_key(), algorithm=self.algorithm)
        except Exception as e:
            logger.error(f"JWT signing failed: {e}", exc_info=True)
            raise InvalidKeyError(f"Failed to sign token: {e}") from e

    def verify(self, token: str) -> dict[str, Any]:
        """Verify a JWT token and return claims.

        Validates:
        - Algorithm matches expected (prevents algorithm confusion attacks)
        - Token signature is valid
        - Token has not expired (exp claim)
        - Token was issued at valid time (iat claim)
        - Issuer matches if configured (iss claim)
        - Audience matches if configured (aud claim)

        **Feature: api-base-score-100, Property 2: Algorithm Mismatch Rejection**
        **Validates: Requirements 1.3**

        Args:
            token: JWT token string to verify.

        Returns:
            Decoded claims dictionary.

        Raises:
            AlgorithmMismatchError: If token algorithm doesn't match expected.
            InvalidKeyError: If verification fails.
        """
        # Extract and validate algorithm from header
        try:
            header = jwt.get_unverified_header(token)
        except JWTError as e:
            raise InvalidKeyError(f"Cannot decode token header: {e}") from e

        token_alg = header.get("alg", "")

        # Prevent 'none' algorithm attack
        if token_alg.lower() == "none":
            raise AlgorithmMismatchError(self.algorithm, "none")

        # Prevent algorithm confusion attack
        if token_alg != self.algorithm:
            raise AlgorithmMismatchError(self.algorithm, token_alg)

        # Configure verification options
        options = {
            "verify_exp": True,
            "verify_iat": True,
            "verify_iss": bool(self._issuer),
            "verify_aud": bool(self._audience),
        }

        # Verify token
        try:
            return jwt.decode(
                token,
                self._get_verification_key(),
                algorithms=[self.algorithm],
                issuer=self._issuer,
                audience=self._audience,
                options=options,
            )
        except JWTError as e:
            error_msg = str(e).lower()
            if "signature" in error_msg:
                raise InvalidKeyError("Token signature verification failed") from e
            logger.warning(f"JWT verification failed: {e}")
            raise InvalidKeyError(f"Token verification failed: {e}") from e
