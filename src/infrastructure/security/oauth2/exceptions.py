"""OAuth2 exceptions.

**Feature: code-review-refactoring, Task 5.4: Extract exceptions module**
**Validates: Requirements 4.1**
"""


class OAuthError(Exception):
    """Base OAuth error."""

    def __init__(self, message: str, error_code: str = "OAUTH_ERROR") -> None:
        super().__init__(message)
        self.error_code = error_code


class OAuthConfigError(OAuthError):
    """OAuth configuration error."""

    def __init__(self, message: str) -> None:
        super().__init__(message, "OAUTH_CONFIG_ERROR")


class OAuthTokenError(OAuthError):
    """OAuth token exchange error."""

    def __init__(self, message: str) -> None:
        super().__init__(message, "OAUTH_TOKEN_ERROR")


class OAuthUserInfoError(OAuthError):
    """OAuth user info retrieval error."""

    def __init__(self, message: str) -> None:
        super().__init__(message, "OAUTH_USERINFO_ERROR")


class OAuthStateError(OAuthError):
    """OAuth state validation error."""

    def __init__(self, message: str) -> None:
        super().__init__(message, "OAUTH_STATE_ERROR")
