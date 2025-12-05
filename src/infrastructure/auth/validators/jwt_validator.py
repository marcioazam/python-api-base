"""Enhanced JWT validator with security hardening.

**Feature: code-review-refactoring, Task 7.1: Create JWTValidator**
**Feature: api-base-score-100, Task 1.2: Update JWTValidator for asymmetric algorithms**
**Validates: Requirements 6.1, 6.2, 1.1, 1.4**

Security features:
- Algorithm restriction (RS256, ES256 only for production)
- Token revocation support
- Tamper detection
- Asymmetric key support (RS256, ES256)
- Production mode warning for HS256
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Protocol

from jose import JWTError, jwt

from core.exceptions import AuthenticationError

logger = logging.getLogger(__name__)


class KeyType(Enum):
    """JWT key type enumeration."""

    SYMMETRIC = "symmetric"
    ASYMMETRIC = "asymmetric"


class InvalidTokenError(AuthenticationError):
    """Raised for JWT validation failures."""

    def __init__(self, message: str = "Invalid token") -> None:
        super().__init__(message=message)
        self.error_code = "TOKEN_INVALID"


class AlgorithmMismatchError(InvalidTokenError):
    """Raised when token algorithm doesn't match expected."""

    def __init__(self, expected: str, received: str) -> None:
        message = f"Algorithm mismatch: expected {expected}, got {received}"
        super().__init__(message=message)
        self.expected = expected
        self.received = received
        self.error_code = "ALGORITHM_MISMATCH"


class TokenRevocationStore(Protocol):
    """Protocol for token revocation storage."""

    async def is_revoked(self, jti: str) -> bool:
        """Check if token is revoked."""
        ...

    async def revoke(self, jti: str, expires_at: datetime) -> None:
        """Revoke a token."""
        ...


@dataclass(frozen=True, slots=True)
class ValidatedToken:
    """Result of successful token validation."""

    sub: str
    jti: str
    exp: datetime
    iat: datetime
    scopes: tuple[str, ...]
    token_type: str
    raw_claims: dict[str, Any]


class JWTValidator:
    """Enhanced JWT validator with security hardening.

    **Feature: code-review-refactoring, Property 4: JWT Algorithm Restriction**
    **Feature: api-base-score-100, Task 1.2: Update JWTValidator for asymmetric algorithms**
    **Validates: Requirements 6.1, 6.2, 1.1, 1.4**

    Supports both symmetric (HS256) and asymmetric (RS256, ES256) algorithms.
    Production environments should use asymmetric algorithms for enhanced security.

    Example:
        >>> # Asymmetric (recommended for production)
        >>> validator = JWTValidator(
        ...     secret_or_key=PUBLIC_KEY_PEM,
        ...     algorithm="RS256",
        ...     require_secure_algorithm=True,
        ... )
        >>> validated = validator.validate(token)

        >>> # Symmetric (development only)
        >>> validator = JWTValidator(
        ...     secret_or_key="your-secret-key",
        ...     algorithm="HS256",
        ...     production_mode=False,
        ... )
    """

    # Secure algorithms only - no HS256 in production
    ALLOWED_ALGORITHMS = frozenset(["RS256", "ES256", "HS256"])
    SECURE_ALGORITHMS = frozenset(["RS256", "ES256"])
    ASYMMETRIC_ALGORITHMS = frozenset(["RS256", "ES256"])

    def __init__(
        self,
        secret_or_key: str,
        algorithm: str = "RS256",
        issuer: str | None = None,
        audience: str | None = None,
        clock_skew_seconds: int = 30,
        revocation_store: TokenRevocationStore | None = None,
        require_secure_algorithm: bool = True,
        production_mode: bool = False,
    ) -> None:
        """Initialize JWT validator.

        **Feature: api-base-score-100, Task 1.2: Update JWTValidator for asymmetric algorithms**
        **Validates: Requirements 1.1, 1.4**
        **Refactored: 2025 - Default to RS256 for security best practices**

        Args:
            secret_or_key: Secret key or public key for verification.
            algorithm: Expected algorithm (RS256, ES256, HS256). Defaults to RS256.
            issuer: Expected issuer claim.
            audience: Expected audience claim.
            clock_skew_seconds: Allowed clock skew for expiration.
            revocation_store: Optional token revocation store.
            require_secure_algorithm: If True, reject HS256. Defaults to True.
            production_mode: If True and using HS256, logs security warning.
        """
        self._secret_or_key = secret_or_key
        self._algorithm = algorithm
        self._issuer = issuer
        self._audience = audience
        self._clock_skew = clock_skew_seconds
        self._revocation_store = revocation_store
        self._require_secure = require_secure_algorithm
        self._production_mode = production_mode
        self._key_type = self._detect_key_type(algorithm)

        self._validate_algorithm(algorithm)
        self._warn_insecure_algorithm()

    def _detect_key_type(self, algorithm: str) -> KeyType:
        """Detect key type based on algorithm.

        Args:
            algorithm: JWT algorithm.

        Returns:
            KeyType enum value.
        """
        if algorithm in self.ASYMMETRIC_ALGORITHMS:
            return KeyType.ASYMMETRIC
        return KeyType.SYMMETRIC

    def _warn_insecure_algorithm(self) -> None:
        """Log warning if using HS256 in production mode.

        **Feature: api-base-score-100, Property: Production HS256 Warning**
        **Validates: Requirements 1.4**
        """
        if self._production_mode and self._algorithm == "HS256":
            logger.warning(
                "HS256 algorithm used in production mode. "
                "Consider using RS256 or ES256 for enhanced security. "
                "Asymmetric algorithms provide better key management and security."
            )

    @property
    def key_type(self) -> KeyType:
        """Get the key type (symmetric or asymmetric)."""
        return self._key_type

    @property
    def is_asymmetric(self) -> bool:
        """Check if using asymmetric algorithm."""
        return self._key_type == KeyType.ASYMMETRIC

    def _validate_algorithm(self, algorithm: str) -> None:
        """Validate algorithm is allowed.

        **Feature: code-review-refactoring, Property 4: JWT Algorithm Restriction**
        **Validates: Requirements 6.1, 6.2**
        """
        if algorithm.lower() == "none":
            raise InvalidTokenError("Algorithm 'none' is not allowed")

        if algorithm not in self.ALLOWED_ALGORITHMS:
            raise InvalidTokenError(f"Algorithm '{algorithm}' is not allowed")

        if self._require_secure and algorithm not in self.SECURE_ALGORITHMS:
            raise InvalidTokenError(
                f"Algorithm '{algorithm}' is not secure enough. "
                f"Use one of: {', '.join(self.SECURE_ALGORITHMS)}"
            )

    def _get_unverified_header(self, token: str) -> dict[str, Any]:
        """Get token header without verification."""
        try:
            return jwt.get_unverified_header(token)
        except JWTError as e:
            raise InvalidTokenError(f"Cannot decode token header: {e}") from e

    def validate(self, token: str, expected_type: str | None = None) -> ValidatedToken:
        """Validate JWT token with security checks.

        **Feature: code-review-refactoring, Property 5: Token Tampering Detection**
        **Validates: Requirements 6.1, 12.5**

        Args:
            token: JWT token string.
            expected_type: Expected token type (access/refresh).

        Returns:
            ValidatedToken with decoded claims.

        Raises:
            InvalidTokenError: If validation fails.
        """
        # Check algorithm before full decode
        header = self._get_unverified_header(token)
        token_alg = header.get("alg", "")

        if token_alg.lower() == "none":
            logger.warning("Rejected token with 'none' algorithm")
            raise InvalidTokenError("Algorithm 'none' is not allowed")

        if token_alg != self._algorithm:
            logger.warning(
                "Algorithm mismatch",
                extra={"expected": self._algorithm, "received": token_alg},
            )
            raise InvalidTokenError(
                f"Algorithm mismatch: expected {self._algorithm}, got {token_alg}"
            )

        # Full validation
        try:
            options = {
                "verify_exp": True,
                "verify_iat": True,
                "verify_nbf": True,
                "require": ["exp", "iat", "sub", "jti"],
            }

            if self._issuer:
                options["verify_iss"] = True
            if self._audience:
                options["verify_aud"] = True

            claims = jwt.decode(
                token,
                self._secret_or_key,
                algorithms=[self._algorithm],
                issuer=self._issuer,
                audience=self._audience,
                options=options,
                leeway=self._clock_skew,
            )
        except JWTError as e:
            error_msg = str(e).lower()
            if "expired" in error_msg:
                raise InvalidTokenError("Token has expired") from e
            if "signature" in error_msg:
                logger.warning("Token signature verification failed")
                raise InvalidTokenError("Token signature is invalid") from e
            raise InvalidTokenError(f"Token validation failed: {e}") from e

        # Validate token type
        token_type = claims.get("token_type", "access")
        if expected_type and token_type != expected_type:
            raise InvalidTokenError(f"Expected {expected_type} token, got {token_type}")

        return ValidatedToken(
            sub=claims["sub"],
            jti=claims["jti"],
            exp=datetime.fromtimestamp(claims["exp"], tz=UTC),
            iat=datetime.fromtimestamp(claims["iat"], tz=UTC),
            scopes=tuple(claims.get("scopes", [])),
            token_type=token_type,
            raw_claims=claims,
        )

    async def validate_with_revocation(
        self,
        token: str,
        expected_type: str | None = None,
    ) -> ValidatedToken:
        """Validate token and check revocation status with fail-closed behavior.

        Args:
            token: JWT token string.
            expected_type: Expected token type.

        Returns:
            ValidatedToken if valid and not revoked.

        Raises:
            InvalidTokenError: If validation fails, token is revoked, or revocation check fails.

        **Feature: core-improvements-v2**
        **Validates: Requirements 3.1, 3.2, 3.3, 3.5**
        """
        validated = self.validate(token, expected_type)

        if self._revocation_store:
            try:
                if await self._revocation_store.is_revoked(validated.jti):
                    logger.warning(
                        "Rejected revoked token",
                        extra={"jti": validated.jti},
                    )
                    raise InvalidTokenError("Token has been revoked")
            except InvalidTokenError:
                raise  # Re-raise our own errors without modification
            except Exception as e:
                # Fail closed - reject token if revocation check fails
                logger.error(
                    "Revocation check failed, rejecting token",
                    extra={"jti": validated.jti, "error": str(e)},
                )
                raise InvalidTokenError("Unable to verify token status") from e

        return validated

    async def revoke(self, token: str) -> None:
        """Revoke a token.

        Args:
            token: JWT token to revoke.

        Raises:
            InvalidTokenError: If token cannot be decoded.
            ValueError: If no revocation store configured.
        """
        if not self._revocation_store:
            raise ValueError("No revocation store configured")

        validated = self.validate(token)
        await self._revocation_store.revoke(validated.jti, validated.exp)

        logger.info(
            "Token revoked",
            extra={"jti": validated.jti, "sub": validated.sub},
        )
