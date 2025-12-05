"""JWKS endpoint for public key distribution.

**Feature: api-best-practices-review-2025**
**Validates: Requirements 20.2, 20.3, 20.4**

Provides /.well-known/jwks.json endpoint for JWT verification by clients.
"""

import logging
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from core.config import (
    JWKS_CACHE_MAX_AGE_SECONDS,
    JWKS_STALE_WHILE_REVALIDATE_SECONDS,
    OPENID_CONFIG_CACHE_MAX_AGE_SECONDS,
)
from infrastructure.auth.jwt.jwks import get_jwks_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Security"])


@router.get(
    "/.well-known/jwks.json",
    summary="Get JSON Web Key Set",
    description="""
    Returns the JSON Web Key Set (JWKS) containing public keys for JWT verification.

    This endpoint is used by clients to:
    - Verify JWT token signatures
    - Lookup keys by kid (Key ID) from token header
    - Handle key rotation transparently

    **Standards Compliance:**
    - RFC 7517: JSON Web Key (JWK)
    - RFC 7518: JSON Web Algorithms (JWA)

    **Security Notes:**
    - Only public keys are exposed (never private keys)
    - Keys have associated kid for lookup
    - Supports key rotation with grace period
    """,
    response_class=JSONResponse,
    responses={
        200: {
            "description": "JWKS containing public keys",
            "content": {
                "application/json": {
                    "example": {
                        "keys": [
                            {
                                "kty": "RSA",
                                "kid": "abc123def456",
                                "use": "sig",
                                "alg": "RS256",
                                "n": "0vx7agoebG...",
                                "e": "AQAB",
                            }
                        ]
                    }
                }
            },
        }
    },
)
async def get_jwks(request: Request) -> JSONResponse:  # noqa: ARG001
    """Get the JSON Web Key Set.

    **Feature: api-best-practices-review-2025**
    **Validates: Requirements 20.2**

    Returns:
        JSONResponse with JWKS containing all active public keys.
    """
    jwks_service = get_jwks_service()
    jwks = jwks_service.get_jwks()

    # Add cache headers for JWKS
    headers = {
        "Cache-Control": (
            f"public, max-age={JWKS_CACHE_MAX_AGE_SECONDS}, "
            f"stale-while-revalidate={JWKS_STALE_WHILE_REVALIDATE_SECONDS}"
        ),
        "Content-Type": "application/json",
    }

    return JSONResponse(content=jwks.to_dict(), headers=headers)


@router.get(
    "/.well-known/openid-configuration",
    summary="OpenID Connect Discovery",
    description="""
    Returns OpenID Connect discovery document with JWKS endpoint.

    Useful for clients implementing OIDC or JWT verification.
    """,
    response_class=JSONResponse,
)
async def openid_configuration(request: Request) -> JSONResponse:
    """Get OpenID Connect discovery document.

    Returns minimal discovery document pointing to JWKS endpoint.
    """
    base_url = str(request.base_url).rstrip("/")

    discovery: dict[str, Any] = {
        "issuer": base_url,
        "jwks_uri": f"{base_url}/.well-known/jwks.json",
        "token_endpoint_auth_methods_supported": ["private_key_jwt"],
        "id_token_signing_alg_values_supported": ["RS256", "ES256"],
        "subject_types_supported": ["public"],
        "response_types_supported": ["token"],
    }

    headers = {
        "Cache-Control": f"public, max-age={OPENID_CONFIG_CACHE_MAX_AGE_SECONDS}",
        "Content-Type": "application/json",
    }

    return JSONResponse(content=discovery, headers=headers)
