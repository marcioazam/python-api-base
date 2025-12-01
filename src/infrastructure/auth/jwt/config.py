"""JWT configuration and key management.

**Feature: api-base-score-100**
**Validates: Requirements 1.1, 1.2**
"""

from dataclasses import dataclass

from .exceptions import InvalidKeyError


@dataclass(frozen=True, slots=True)
class JWTKeyConfig:
    """JWT key configuration for asymmetric algorithms.

    Attributes:
        algorithm: JWT algorithm (RS256, ES256, HS256).
        private_key: Private key for signing (RS256/ES256).
        public_key: Public key for verification (RS256/ES256).
        secret_key: Secret key for HS256.

    Example:
        >>> # RS256 configuration
        >>> config = JWTKeyConfig(
        ...     algorithm="RS256",
        ...     private_key=PRIVATE_KEY_PEM,
        ...     public_key=PUBLIC_KEY_PEM,
        ... )

        >>> # HS256 configuration
        >>> config = JWTKeyConfig(
        ...     algorithm="HS256",
        ...     secret_key="your-secret-key-32-chars-min",
        ... )
    """

    algorithm: str
    private_key: str | None = None
    public_key: str | None = None
    secret_key: str | None = None

    def __post_init__(self) -> None:
        """Validate key configuration.

        Raises:
            InvalidKeyError: If required keys are missing for the algorithm.
        """
        if self.algorithm in ("RS256", "ES256"):
            if not self.private_key and not self.public_key:
                raise InvalidKeyError(
                    f"{self.algorithm} requires private_key or public_key"
                )
        elif self.algorithm == "HS256":
            if not self.secret_key:
                raise InvalidKeyError("HS256 requires secret_key")
        else:
            raise InvalidKeyError(f"Unsupported algorithm: {self.algorithm}")
