"""JWT authentication service for token generation and verification.

**Feature: core-code-review, api-best-practices-review-2025**
**Validates: Requirements 4.1, 4.4, 4.5, 11.1, 20.1, 20.2, 20.3**

**Feature: full-codebase-review-2025, Task 1.3: Refactored for file size compliance**
"""

from .errors import TokenExpiredError, TokenInvalidError, TokenRevokedError
from .jwks import (
    JWKSService,
    get_jwks_service,
    initialize_jwks_service,
)
from .jwks_models import (
    JWK,
    JWKSResponse,
    KeyEntry,
    generate_kid_from_public_key,
    create_jwk_from_rsa_public_key,
    create_jwk_from_ec_public_key,
)
from .models import TokenPair, TokenPayload
from .protocols import KidNotFoundError
from .providers import ES256Provider, HS256Provider, RS256Provider
from .service import JWTService
from .time_source import SystemTimeSource, TimeSource

__all__ = [
    # Service
    "JWTService",
    # Providers
    "RS256Provider",
    "ES256Provider",
    "HS256Provider",
    # JWKS Service
    "JWKSService",
    "get_jwks_service",
    "initialize_jwks_service",
    # JWKS Models
    "JWK",
    "JWKSResponse",
    "KeyEntry",
    "generate_kid_from_public_key",
    "create_jwk_from_rsa_public_key",
    "create_jwk_from_ec_public_key",
    # Time
    "SystemTimeSource",
    "TimeSource",
    # Errors
    "TokenExpiredError",
    "TokenInvalidError",
    "TokenRevokedError",
    "KidNotFoundError",
    # Models
    "TokenPair",
    "TokenPayload",
]
