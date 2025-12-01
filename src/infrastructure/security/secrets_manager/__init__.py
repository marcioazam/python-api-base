"""Secrets management with multi-provider support.

**Feature: code-review-refactoring, Task 18.1: Refactor secrets_manager.py**
**Validates: Requirements 5.7**
"""

from .cache import InMemorySecretCache, SecretCache
from .enums import SecretProvider, SecretType
from .exceptions import (
    SecretAccessDeniedError,
    SecretNotFoundError,
    SecretRotationError,
    SecretsError,
)
from .manager import SecretsManager
from .models import RotationConfig, SecretMetadata, SecretValue
from .providers import BaseSecretsProvider, LocalSecretsProvider

__all__ = [
    "BaseSecretsProvider",
    "InMemorySecretCache",
    "LocalSecretsProvider",
    "RotationConfig",
    "SecretAccessDeniedError",
    "SecretCache",
    "SecretMetadata",
    "SecretNotFoundError",
    "SecretProvider",
    "SecretRotationError",
    "SecretType",
    "SecretValue",
    "SecretsError",
    "SecretsManager",
]
