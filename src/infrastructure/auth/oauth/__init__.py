"""Generic OAuth providers with PEP 695 type parameters.

**Feature: enterprise-generics-2025**
**Requirement: R13 - Generic Authentication System**

Exports:
    - OAuthProvider[TUser, TClaims]: Generic OAuth provider protocol
    - KeycloakProvider[TUser, TClaims]: Keycloak implementation
    - Auth0Provider[TUser, TClaims]: Auth0 implementation
    - AuthResult[TUser, TClaims]: Authentication result
    - TokenPair[TClaims]: Access/refresh token pair
"""

from infrastructure.auth.oauth.provider import (
    OAuthProvider,
    AuthResult,
    TokenPair,
    AuthError,
    OAuthConfig,
)
from infrastructure.auth.oauth.keycloak import KeycloakProvider, KeycloakConfig
from infrastructure.auth.oauth.auth0 import Auth0Provider, Auth0Config

__all__ = [
    # Core
    "OAuthProvider",
    "AuthResult",
    "TokenPair",
    "AuthError",
    "OAuthConfig",
    # Keycloak
    "KeycloakProvider",
    "KeycloakConfig",
    # Auth0
    "Auth0Provider",
    "Auth0Config",
]
