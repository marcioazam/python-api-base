"""OAuth2/OIDC provider for external authentication.

**Feature: code-review-refactoring, Task 5.9: Create __init__.py with re-exports**
**Validates: Requirements 1.2, 4.5**

Original: oauth2.py (454 lines)
Refactored: oauth2/ package (8 files, ~40-140 lines each)

Supports Google, GitHub, Azure AD and generic OIDC providers.

Usage:
    from my_api.shared.oauth2 import (
        GoogleOAuthProvider,
        GitHubOAuthProvider,
        OAuthConfig,
        OAuthUserInfo,
    )
"""

# Backward compatible re-exports
from .base import BaseOAuthProvider
from .enums import OAuthProvider, PROVIDER_CONFIGS
from .exceptions import (
    OAuthConfigError,
    OAuthError,
    OAuthStateError,
    OAuthTokenError,
    OAuthUserInfoError,
)
from .models import OAuthConfig, OAuthState, OAuthTokenResponse, OAuthUserInfo
from .providers.github import GitHubOAuthProvider
from .providers.google import GoogleOAuthProvider
from .state_store import InMemoryStateStore, StateStore

__all__ = [
    # Enums
    "OAuthProvider",
    "PROVIDER_CONFIGS",
    # Models
    "OAuthConfig",
    "OAuthUserInfo",
    "OAuthTokenResponse",
    "OAuthState",
    # Base
    "BaseOAuthProvider",
    # Providers
    "GoogleOAuthProvider",
    "GitHubOAuthProvider",
    # State Store
    "StateStore",
    "InMemoryStateStore",
    # Exceptions
    "OAuthError",
    "OAuthConfigError",
    "OAuthTokenError",
    "OAuthUserInfoError",
    "OAuthStateError",
]
