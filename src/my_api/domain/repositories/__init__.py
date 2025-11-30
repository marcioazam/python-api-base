"""Domain repository interfaces.

**Feature: domain-code-review-fixes**
**Validates: Requirements 2.1, 3.1**
"""

from my_api.domain.repositories.base import (
    ReadOnlyRepositoryProtocol,
    RepositoryProtocol,
)

__all__ = [
    "ReadOnlyRepositoryProtocol",
    "RepositoryProtocol",
]
