"""JWT algorithm provider implementations.

**Feature: api-base-score-100, Task 1.1: Add RS256/ES256 provider classes**
**Validates: Requirements 1.1, 1.2, 1.4**
"""

import logging
from datetime import timedelta

from .exceptions import InvalidKeyError
from .protocols import BaseJWTProvider

logger = logging.getLogger(__name__)


class RS256Provider(BaseJWTProvider):
    """RS256 (RSA + SHA-256) provider for asymmetric JWT.

    **Feature: api-base-score-100, Task 1.1: Add RS256/ES256 provider classes**
    **Validates: Requirements 1.1, 1.2**

    Uses RSA private key for signing and public key for verification.
    Recommended for production environments where key distribution is a concern.

    Security Features:
        - Asymmetric cryptography (public/private key pair)
        - RSA 2048-bit keys recommended
        - PEM format support
        - Prevents algorithm confusion attacks

    Example:
        >>> provider = RS256Provider(
        ...     private_key=PRIVATE_KEY_PEM,
        ...     public_key=PUBLIC_KEY_PEM,
        ...     issuer="my-api",
        ...     audience="my-app",
        ... )
        >>> token = provider.sign({"sub": "user123", "roles": ["admin"]})
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
            private_key: RSA private key in PEM format (required for signing).
            public_key: RSA public key in PEM format (required for verification).
            issuer: Token issuer claim (iss). Optional.
            audience: Token audience claim (aud). Optional.
            default_expiry: Default token expiration time. Default: 1 hour.

        Raises:
            InvalidKeyError: If neither private nor public key provided,
                or if key format is invalid.
        """
        super().__init__(issuer, audience, default_expiry)

        if not private_key and not public_key:
            raise InvalidKeyError(
                "RS256 requires at least one of private_key or public_key"
            )

        self._private_key = private_key
        self._public_key = public_key

        self._validate_keys()

    def _validate_keys(self) -> None:
        """Validate RSA key format.

        Raises:
            InvalidKeyError: If key format is invalid.
        """
        if self._private_key:
            if "-----BEGIN" not in self._private_key:
                raise InvalidKeyError(
                    "Invalid RSA private key format. Expected PEM format "
                    "(must start with -----BEGIN)."
                )
        if self._public_key:
            if "-----BEGIN" not in self._public_key:
                raise InvalidKeyError(
                    "Invalid RSA public key format. Expected PEM format "
                    "(must start with -----BEGIN)."
                )

    @property
    def algorithm(self) -> str:
        """Get the algorithm name."""
        return "RS256"

    def _get_signing_key(self) -> str:
        """Get RSA private key for signing.

        Returns:
            RSA private key in PEM format.

        Raises:
            InvalidKeyError: If private key not provided.
        """
        if not self._private_key:
            raise InvalidKeyError("Private key required for signing")
        return self._private_key

    def _get_verification_key(self) -> str:
        """Get RSA public key for verification.

        Returns:
            RSA public key in PEM format. Falls back to private key if public key
            is not provided (jose library can extract public key from private key).

        Raises:
            InvalidKeyError: If neither public nor private key provided.
        """
        if self._public_key:
            return self._public_key
        if self._private_key:
            # jose library can extract public key from private key
            return self._private_key
        raise InvalidKeyError("Public key required for verification")


class ES256Provider(BaseJWTProvider):
    """ES256 (ECDSA + SHA-256) provider for asymmetric JWT.

    **Feature: api-base-score-100, Task 1.1: Add RS256/ES256 provider classes**
    **Validates: Requirements 1.1, 1.2**

    Uses ECDSA private key for signing and public key for verification.
    More compact signatures than RS256, ideal for bandwidth-constrained
    environments (mobile, IoT).

    Security Features:
        - Asymmetric cryptography (public/private key pair)
        - ECDSA P-256 curve
        - Smaller signatures than RS256 (~132 bytes vs ~256 bytes)
        - PEM format support

    Example:
        >>> provider = ES256Provider(
        ...     private_key=PRIVATE_KEY_PEM,
        ...     public_key=PUBLIC_KEY_PEM,
        ...     issuer="my-api",
        ...     audience="my-app",
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
            private_key: ECDSA private key in PEM format (required for signing).
            public_key: ECDSA public key in PEM format (required for verification).
            issuer: Token issuer claim (iss). Optional.
            audience: Token audience claim (aud). Optional.
            default_expiry: Default token expiration time. Default: 1 hour.

        Raises:
            InvalidKeyError: If neither private nor public key provided,
                or if key format is invalid.
        """
        super().__init__(issuer, audience, default_expiry)

        if not private_key and not public_key:
            raise InvalidKeyError(
                "ES256 requires at least one of private_key or public_key"
            )

        self._private_key = private_key
        self._public_key = public_key

        self._validate_keys()

    def _validate_keys(self) -> None:
        """Validate ECDSA key format.

        Raises:
            InvalidKeyError: If key format is invalid.
        """
        if self._private_key:
            if "-----BEGIN" not in self._private_key:
                raise InvalidKeyError(
                    "Invalid ECDSA private key format. Expected PEM format "
                    "(must start with -----BEGIN)."
                )
        if self._public_key:
            if "-----BEGIN" not in self._public_key:
                raise InvalidKeyError(
                    "Invalid ECDSA public key format. Expected PEM format "
                    "(must start with -----BEGIN)."
                )

    @property
    def algorithm(self) -> str:
        """Get the algorithm name."""
        return "ES256"

    def _get_signing_key(self) -> str:
        """Get ECDSA private key for signing.

        Returns:
            ECDSA private key in PEM format.

        Raises:
            InvalidKeyError: If private key not provided.
        """
        if not self._private_key:
            raise InvalidKeyError("Private key required for signing")
        return self._private_key

    def _get_verification_key(self) -> str:
        """Get ECDSA public key for verification.

        Returns:
            ECDSA public key in PEM format. Falls back to private key if public key
            is not provided (jose library can extract public key from private key).

        Raises:
            InvalidKeyError: If neither public nor private key provided.
        """
        if self._public_key:
            return self._public_key
        if self._private_key:
            # jose library can extract public key from private key
            return self._private_key
        raise InvalidKeyError("Public key required for verification")


class HS256Provider(BaseJWTProvider):
    """HS256 (HMAC + SHA-256) provider for symmetric JWT.

    **Feature: api-base-score-100, Task 1.1: Add RS256/ES256 provider classes**
    **Validates: Requirements 1.4**

    Uses shared secret for both signing and verification.

    **SECURITY WARNING**:
        - NOT recommended for production environments
        - Symmetric algorithm means same key for signing and verification
        - Anyone with the key can both create and verify tokens
        - Use RS256 or ES256 instead for production
        - Only use HS256 for development/testing

    Example:
        >>> # Development only - NOT for production!
        >>> provider = HS256Provider(
        ...     secret_key="dev-secret-key-minimum-32-chars",
        ...     production_mode=False,  # Will warn if True
        ... )
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
            secret_key: Shared secret for signing/verification (min 32 chars).
            issuer: Token issuer claim (iss). Optional.
            audience: Token audience claim (aud). Optional.
            default_expiry: Default token expiration time. Default: 1 hour.
            production_mode: If True, logs security warning about HS256 usage.

        Raises:
            InvalidKeyError: If secret_key is empty or too short.
        """
        super().__init__(issuer, audience, default_expiry)

        if not secret_key or len(secret_key) < 32:
            raise InvalidKeyError(
                "HS256 secret_key must be at least 32 characters for security"
            )

        self._secret_key = secret_key

        if production_mode:
            logger.warning(
                "SECURITY WARNING: HS256 algorithm used in production mode. "
                "HS256 is a symmetric algorithm and NOT recommended for production. "
                "Consider using RS256 or ES256 for enhanced security.",
                extra={
                    "algorithm": "HS256",
                    "operation": "INIT",
                    "security_level": "LOW",
                },
            )

    @property
    def algorithm(self) -> str:
        """Get the algorithm name."""
        return "HS256"

    def _get_signing_key(self) -> str:
        """Get secret key for signing.

        Returns:
            Shared secret key.
        """
        return self._secret_key

    def _get_verification_key(self) -> str:
        """Get secret key for verification.

        Returns:
            Shared secret key (same as signing key).
        """
        return self._secret_key
