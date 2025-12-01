"""Secrets manager enums.

**Feature: code-review-refactoring, Task 18.1: Refactor secrets_manager.py**
**Validates: Requirements 5.7**
"""

from enum import Enum


class SecretProvider(str, Enum):
    """Supported secret providers."""

    AWS_SECRETS_MANAGER = "aws_secrets_manager"
    HASHICORP_VAULT = "hashicorp_vault"
    AZURE_KEY_VAULT = "azure_key_vault"
    GCP_SECRET_MANAGER = "gcp_secret_manager"
    LOCAL = "local"


class SecretType(str, Enum):
    """Types of secrets."""

    STRING = "string"
    JSON = "json"
    BINARY = "binary"
    KEY_VALUE = "key_value"
