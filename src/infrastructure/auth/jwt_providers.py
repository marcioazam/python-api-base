"""JWT Algorithm Providers with asymmetric key support.

This module has been refactored into smaller, focused modules:
- jwt/exceptions.py: JWT-specific exceptions
- jwt/config.py: Configuration and key management
- jwt/protocols.py: Protocols and base classes
- jwt/providers.py: Concrete provider implementations (RS256, ES256, HS256)
- jwt/factory.py: Provider factory function

This file now serves as a compatibility layer, re-exporting all components.

**Feature: api-base-score-100, Task 1.1: Add RS256/ES256 provider classes**
**Feature: api-base-score-100, Task 5.1: Add comprehensive docstrings to JWT module**
**Validates: Requirements 1.1, 1.2, 4.1, 4.4**
**Refactored: 2025 - Split 517 lines into 5 focused modules**

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
    >>> from infrastructure.auth.jwt_providers import RS256Provider
    >>> provider = RS256Provider(
    ...     private_key=PRIVATE_KEY_PEM,
    ...     public_key=PUBLIC_KEY_PEM,
    ...     issuer="my-api",
    ...     audience="my-app",
    ... )
    >>> token = provider.sign({"sub": "user123", "roles": ["admin"]})
    >>> claims = provider.verify(token)

    >>> # Development: Use HS256 (not for production!)
    >>> from infrastructure.auth.jwt_providers import HS256Provider
    >>> provider = HS256Provider(secret_key="dev-secret-key-32-chars-min")
    >>> token = provider.sign({"sub": "user123"})
"""

# Re-export all components from refactored modules
from .jwt.exceptions import AlgorithmMismatchError, InvalidKeyError
from .jwt.config import JWTKeyConfig
from .jwt.protocols import BaseJWTProvider, JWTAlgorithmProvider
from .jwt.providers import ES256Provider, HS256Provider, RS256Provider
from .jwt.factory import create_jwt_provider

# Re-export all for public API
__all__ = [
    # Exceptions
    "InvalidKeyError",
    "AlgorithmMismatchError",
    # Configuration
    "JWTKeyConfig",
    # Protocols
    "JWTAlgorithmProvider",
    "BaseJWTProvider",
    # Providers
    "RS256Provider",
    "ES256Provider",
    "HS256Provider",
    # Factory
    "create_jwt_provider",
]
