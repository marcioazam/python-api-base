"""OAuth2 provider enumerations.

**Feature: code-review-refactoring, Task 5.2: Extract enums module**
**Validates: Requirements 4.1**
"""

from enum import Enum


class OAuthProvider(str, Enum):
    """Supported OAuth2 providers."""

    GOOGLE = "google"
    GITHUB = "github"
    AZURE_AD = "azure_ad"
    GENERIC = "generic"


# Provider-specific default configurations
PROVIDER_CONFIGS: dict[OAuthProvider, dict[str, str]] = {
    OAuthProvider.GOOGLE: {
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "userinfo_url": "https://www.googleapis.com/oauth2/v3/userinfo",
        "jwks_url": "https://www.googleapis.com/oauth2/v3/certs",
    },
    OAuthProvider.GITHUB: {
        "authorize_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
        "userinfo_url": "https://api.github.com/user",
        "jwks_url": "",
    },
    OAuthProvider.AZURE_AD: {
        "authorize_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        "token_url": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
        "userinfo_url": "https://graph.microsoft.com/v1.0/me",
        "jwks_url": "https://login.microsoftonline.com/common/discovery/v2.0/keys",
    },
}
