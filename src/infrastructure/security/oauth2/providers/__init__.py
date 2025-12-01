"""OAuth2 provider implementations.

**Feature: code-review-refactoring, Task 5.7-5.8: Extract providers**
**Validates: Requirements 4.2, 4.3**
"""

from .github import GitHubOAuthProvider
from .google import GoogleOAuthProvider

__all__ = ["GoogleOAuthProvider", "GitHubOAuthProvider"]
