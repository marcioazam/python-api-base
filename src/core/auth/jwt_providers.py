"""JWT Algorithm Providers with asymmetric key support.

**Feature: api-base-score-100, Task 1.1: Add RS256/ES256 provider classes**
**Feature: api-base-score-100, Task 5.1: Add comprehensive docstrings to JWT module**
**Validates: Requirements 1.1, 1.2, 4.1, 4.4**

This module provides JWT (JSON Web Token) algorithm providers supporting both
symmetric and asymmetric cryptographic algorithms for token signing and verification.

Security Features:
    - RS256 (RSA + SHA-256): Asymmetric algorithm using RSA keys. Recommended for
      production environments where key distribution is a concern.
    - ES256 (ECDSA + SHA-256): Asymmetric algorithm using elliptic curve keys.
      More compact signatures than RS256, ideal for mobile/IoT applications.
    - HS256 (HMAC + SHA-256): Symmetric algorithm using shared secret.
      NOT recommended for production - use only for development/testing.

Security Notes:
    - Always use asymmetric algorithms (RS256/ES256) in production
    - Keep private keys secure and never expose them in logs or responses
    - Use key rotation policies for long-running applications
    - Validate token algorithm to prevent algorithm confusion attacks
    - Set appropriate token expiration times (default: 1 hour)

Example Usage:
    >>> # Production: Use RS256 with key pair
    >>> from my_api.core.auth.jwt_providers import RS256Provider
    >>> provider = RS256Provider(
    ...     private_key=PRIVATE_KEY_PEM,
    ...     public_key=PUBLIC_KEY_PEM,
    ...     issuer="my-api",
    ...     audience="my-app",
    ... )
    >>> token = provider.sign({"sub": "user123", "roles": ["admin"]})
    >>> claims = provider.verify(token)

    >>> # Development: Use HS256 (not for production!)
    >>> from my_api.core.auth.jwt_providers import HS256Provider
    >>> provider = HS256Provider(secret_key="dev-secret-key-32-chars-min")
    >>> token = provider.sign({"sub": "user123"})
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol, runtime_checkable

from jose import JWTError, jwt

logger = logging.getLogger(__name__)


class InvalidKeyError(Exception):
    """Raised when JWT key format is invalid."""

    def __init__(self, message: str = "Invalid key format") -> None:
        super().__init__(message)
        self.message = message


class AlgorithmMismatchError(Exception):
    """Raised when token algorithm doesn't match expected."""

    def __init__(self, expected: str, received: str) -> None:
        message = f"Algorithm mismatch: expected {expected}, got {received}"
        super().__init__(message)
        self.expected = expected
        self.received = received


@dataclass(frozen=True, slots=True)
class JWTKeyConfig:
    """JWT key configuration for asymmetric algorithms.

    Attributes:
        algorithm: JWT algorithm (RS256, ES256, HS256).
        private_key: Private key for signing (RS256/ES256).
        public_key: Public key for verification (RS256/ES256).
        secret_key: Secret key for HS256.
    """

    algorithm: str
    private_key: str | None = None
    public_key: str | None = None
    secret_key: str | None = None

    def __post_init__(self) -> None:
        """Validate key configuration."""
        if self.algorithm in ("RS256", "ES256"):
            if not self.private_key and not self.public_key:
                raise InvalidKeyError(
                    f"{self.algorithm} requires private_key or public_key"
                )
        elif self.algorithm == "HS256":
            if not self.secret_key:
                raise InvalidKeyError("HS256 requires secret_key")


@runtime_checkable
class JWTAlgorithmProvider(Protocol):
    """Protocol for JWT algorithm providers.

    **Feature: api-base-score-100, Property 1: RS256 Sign-Verify Round Trip**
    **Validates: Requirements 1.2**
    """

    @property
    def algorithm(self) -> str:
        """Get the algorithm name."""
        ...

    def sign(self, payload: dict[str, Any], expires_delta: timedelta | None = None) -> str:
        """Sign a payload and return JWT token.

        Args:
            payload: Claims to include in token.
            expires_delta: Token expiration time.

        Returns:
            Signed JWT token string.
        """
        ...

    def verify(self, token: str) -> dict[str, Any]:
        """Verify a JWT token and return claims.

        Args:
            token: JWT token string.

        Returns:
            Decoded claims dictionary.

        Raises:
            AlgorithmMismatchError: If token algorithm doesn't match.
            InvalidKeyError: If key format is invalid.
        """
        ...


class BaseJWTProvider(ABC):
    """Base class for JWT providers with common functionality."""

    def __init__(
        self,
        issuer: str | None = None,
        audience: str | None = None,
        default_expiry: timedelta = timedelta(hours=1),
    ) -> None:
        """Initialize base JWT provider.

        Args:
            issuer: Token issuer claim.
            audience: Token audience claim.
            default_expiry: Default token expiration time.
        """
        self._issuer = issuer
        self._audience = audience
        self._default_expiry = default_expiry

    @property
    @abstractmethod
    def algorithm(self) -> str:
        """Get the algorithm name."""
        ...

    @abstractmethod
    def _get_signing_key(self) -> str:
        """Get key for signing."""
        ...

    @abstractmethod
    def _get_verification_key(self) -> str:
        """Get key for verification."""
        ...

    def sign(self, payload: dict[str, Any], expires_delta: timedelta | None = None) -> str:
        """Sign a payload and return JWT token.

        **Feature: api-base-score-100, Property 1: RS256 Sign-Verify Round Trip**
        **Validates: Requirements 1.2**

        Args:
            payload: Claims to include in token.
            expires_delta: Token expiration time.

        Returns:
            Signed JWT token string.
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
            raise InvalidKeyError(f"Failed to sign token: {e}") from e

    def verify(self, token: str) -> dict[str, Any]:
        """Verify a JWT token and return claims.

        **Feature: api-base-score-100, Property 2: Algorithm Mismatch Rejection**
        **Validates: Requirements 1.3**

        Args:
            token: JWT token string.

        Returns:
            Decoded claims dictionary.

        Raises:
            AlgorithmMismatchError: If token algorithm doesn't match.
            InvalidKeyError: If key format is invalid.
        """
        try:
            header = jwt.get_unverified_header(token)
        except JWTError as e:
            raise InvalidKeyError(f"Cannot decode token header: {e}") from e

        token_alg = header.get("alg", "")

        if token_alg.lower() == "none":
            raise AlgorithmMismatchError(self.algorithm, "none")

        if token_alg != self.algorithm:
            raise AlgorithmMismatchError(self.algorithm, token_alg)

        options = {
            "verify_exp": True,
            "verify_iat": True,
            "verify_iss": bool(self._issuer),
            "verify_aud": bool(self._audience),
        }

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
            raise InvalidKeyError(f"Token verification failed: {e}") from e


class RS256Provider(BaseJWTProvider):
    """RS256 (RSA + SHA-256) provider for asymmetric JWT.

    **Feature: api-base-score-100, Task 1.1: Add RS256/ES256 provider classes**
    **Validates: Requirements 1.1, 1.2**

    Uses RSA private key for signing and public key for verification.
    Recommended for production environments.

    Example:
        >>> provider = RS256Provider(
        ...     private_key=PRIVATE_KEY_PEM,
        ...     public_key=PUBLIC_KEY_PEM,
        ... )
        >>> token = provider.sign({"sub": "user123"})
        >>> claims = provider.verify(token)
    """

    def __init__(
        self,
        private_key: str | None = None,
        public_key: str | None = None,
        issuer: str | None = None,
        audience: str | None = None,
        default_expiry: timedelta = timedelta(hours=1),
    ) -> None:
        """Initialize RS256 provider.

        Args:
            private_key: RSA private key in PEM format (for signing).
            public_key: RSA public key in PEM format (for verification).
            issuer: Token issuer claim.
            audience: Token audience claim.
            default_expiry: Default token expiration time.

        Raises:
            InvalidKeyError: If neither private nor public key provided.
        """
        super().__init__(issuer, audience, default_expiry)

        if not private_key and not public_key:
            raise InvalidKeyError("RS256 requires at least one of private_key or public_key")

        self._private_key = private_key
        self._public_key = public_key

        self._validate_keys()

    def _validate_keys(self) -> None:
        """Validate RSA key format."""
        if self._private_key:
            if "-----BEGIN" not in self._private_key:
                raise InvalidKeyError(
                    "Invalid RSA private key format. Expected PEM format."
                )
        if self._public_key:
            if "-----BEGIN" not in self._public_key:
                raise InvalidKeyError(
                    "Invalid RSA public key format. Expected PEM format."
                )

    @property
    def algorithm(self) -> str:
        """Get the algorithm name."""
        return "RS256"

    def _get_signing_key(self) -> str:
        """Get RSA private key for signing."""
        if not self._private_key:
            raise InvalidKeyError("Private key required for signing")
        return self._private_key

    def _get_verification_key(self) -> str:
        """Get RSA public key for verification."""
        if self._public_key:
            return self._public_key
        if self._private_key:
            return self._private_key
        raise InvalidKeyError("Public key required for verification")


class ES256Provider(BaseJWTProvider):
    """ES256 (ECDSA + SHA-256) provider for asymmetric JWT.

    **Feature: api-base-score-100, Task 1.1: Add RS256/ES256 provider classes**
    **Validates: Requirements 1.1, 1.2**

    Uses ECDSA private key for signing and public key for verification.
    More compact than RS256, recommended for mobile/IoT.

    Example:
        >>> provider = ES256Provider(
        ...     private_key=PRIVATE_KEY_PEM,
        ...     public_key=PUBLIC_KEY_PEM,
        ... )
        >>> token = provider.sign({"sub": "user123"})
        >>> claims = provider.verify(token)
    """

    def __init__(
        self,
        private_key: str | None = None,
        public_key: str | None = None,
        issuer: str | None = None,
        audience: str | None = None,
        default_expiry: timedelta = timedelta(hours=1),
    ) -> None:
        """Initialize ES256 provider.

        Args:
            private_key: ECDSA private key in PEM format (for signing).
            public_key: ECDSA public key in PEM format (for verification).
            issuer: Token issuer claim.
            audience: Token audience claim.
            default_expiry: Default token expiration time.

        Raises:
            InvalidKeyError: If neither private nor public key provided.
        """
        super().__init__(issuer, audience, default_expiry)

        if not private_key and not public_key:
            raise InvalidKeyError("ES256 requires at least one of private_key or public_key")

        self._private_key = private_key
        self._public_key = public_key

        self._validate_keys()

    def _validate_keys(self) -> None:
        """Validate ECDSA key format."""
        if self._private_key:
            if "-----BEGIN" not in self._private_key:
                raise InvalidKeyError(
                    "Invalid ECDSA private key format. Expected PEM format."
                )
        if self._public_key:
            if "-----BEGIN" not in self._public_key:
                raise InvalidKeyError(
                    "Invalid ECDSA public key format. Expected PEM format."
                )

    @property
    def algorithm(self) -> str:
        """Get the algorithm name."""
        return "ES256"

    def _get_signing_key(self) -> str:
        """Get ECDSA private key for signing."""
        if not self._private_key:
            raise InvalidKeyError("Private key required for signing")
        return self._private_key

    def _get_verification_key(self) -> str:
        """Get ECDSA public key for verification."""
        if self._public_key:
            return self._public_key
        if self._private_key:
            return self._private_key
        raise InvalidKeyError("Public key required for verification")


class HS256Provider(BaseJWTProvider):
    """HS256 (HMAC + SHA-256) provider for symmetric JWT.

    **Feature: api-base-score-100, Task 1.1: Add RS256/ES256 provider classes**
    **Validates: Requirements 1.4**

    Uses shared secret for both signing and verification.
    NOT recommended for production - use RS256 or ES256 instead.

    Example:
        >>> provider = HS256Provider(secret_key="your-secret-key")
        >>> token = provider.sign({"sub": "user123"})
        >>> claims = provider.verify(token)
    """

    def __init__(
        self,
        secret_key: str,
        issuer: str | None = None,
        audience: str | None = None,
        default_expiry: timedelta = timedelta(hours=1),
        production_mode: bool = False,
    ) -> None:
        """Initialize HS256 provider.

        Args:
            secret_key: Shared secret for signing/verification.
            issuer: Token issuer claim.
            audience: Token audience claim.
            default_expiry: Default token expiration time.
            production_mode: If True, logs security warning.

        Raises:
            InvalidKeyError: If secret_key is empty or too short.
        """
        super().__init__(issuer, audience, default_expiry)

        if not secret_key or len(secret_key) < 32:
            raise InvalidKeyError(
                "HS256 secret_key must be at least 32 characters"
            )

        self._secret_key = secret_key

        if production_mode:
            logger.warning(
                "HS256 algorithm used in production mode. "
                "Consider using RS256 or ES256 for enhanced security."
            )

    @property
    def algorithm(self) -> str:
        """Get the algorithm name."""
        return "HS256"

    def _get_signing_key(self) -> str:
        """Get secret key for signing."""
        return self._secret_key

    def _get_verification_key(self) -> str:
        """Get secret key for verification."""
        return self._secret_key


def create_jwt_provider(config: JWTKeyConfig, **kwargs: Any) -> JWTAlgorithmProvider:
    """Factory function to create appropriate JWT provider.

    Args:
        config: JWT key configuration.
        **kwargs: Additional arguments for provider.

    Returns:
        Appropriate JWT provider instance.

    Raises:
        InvalidKeyError: If algorithm is not supported.
    """
    if config.algorithm == "RS256":
        return RS256Provider(
            private_key=config.private_key,
            public_key=config.public_key,
            **kwargs,
        )
    elif config.algorithm == "ES256":
        return ES256Provider(
            private_key=config.private_key,
            public_key=config.public_key,
            **kwargs,
        )
    elif config.algorithm == "HS256":
        if not config.secret_key:
            raise InvalidKeyError("HS256 requires secret_key")
        return HS256Provider(secret_key=config.secret_key, **kwargs)
    else:
        raise InvalidKeyError(f"Unsupported algorithm: {config.algorithm}")
