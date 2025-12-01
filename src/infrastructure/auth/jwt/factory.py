"""JWT provider factory.

**Feature: api-base-score-100**
**Validates: Requirements 1.1**
"""

from typing import Any

from .config import JWTKeyConfig
from .exceptions import InvalidKeyError
from .protocols import JWTAlgorithmProvider
from .providers import ES256Provider, HS256Provider, RS256Provider


def create_jwt_provider(config: JWTKeyConfig, **kwargs: Any) -> JWTAlgorithmProvider:
    """Factory function to create appropriate JWT provider.

    Creates the correct provider instance based on the algorithm specified
    in the configuration.

    **Feature: api-base-score-100**
    **Validates: Requirements 1.1**

    Args:
        config: JWT key configuration with algorithm and keys.
        **kwargs: Additional arguments passed to provider constructor
            (e.g., issuer, audience, default_expiry).

    Returns:
        Appropriate JWT provider instance (RS256, ES256, or HS256).

    Raises:
        InvalidKeyError: If algorithm is not supported or required keys missing.

    Example:
        >>> # Create RS256 provider
        >>> config = JWTKeyConfig(
        ...     algorithm="RS256",
        ...     private_key=PRIVATE_KEY_PEM,
        ...     public_key=PUBLIC_KEY_PEM,
        ... )
        >>> provider = create_jwt_provider(
        ...     config,
        ...     issuer="my-api",
        ...     audience="my-app",
        ... )
        >>> token = provider.sign({"sub": "user123"})

        >>> # Create HS256 provider (dev only)
        >>> config = JWTKeyConfig(
        ...     algorithm="HS256",
        ...     secret_key="dev-secret-key-32-chars-min",
        ... )
        >>> provider = create_jwt_provider(config)
        >>> token = provider.sign({"sub": "user123"})
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
            raise InvalidKeyError("HS256 requires secret_key in configuration")
        return HS256Provider(secret_key=config.secret_key, **kwargs)
    else:
        raise InvalidKeyError(
            f"Unsupported algorithm: {config.algorithm}. "
            f"Supported algorithms: RS256, ES256, HS256"
        )
