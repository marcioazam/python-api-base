"""Secrets provider implementations.

**Feature: shared-modules-code-review-fixes, Task 1.1, 1.2**
**Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5**
"""

from abc import ABC, abstractmethod
from datetime import datetime, UTC
from typing import Any

from .enums import SecretType
from .exceptions import SecretNotFoundError
from .models import SecretMetadata, SecretValue


class BaseSecretsProvider(ABC):
    """Abstract base class for secrets providers.

    Defines the interface that all secrets providers must implement.
    Supports CRUD operations and secret rotation.
    """

    @abstractmethod
    async def get_secret(self, name: str, version: str | None = None) -> SecretValue:
        """Get a secret by name.

        Args:
            name: Secret name/identifier.
            version: Optional version string.

        Returns:
            SecretValue containing the secret data.

        Raises:
            SecretNotFoundError: If secret does not exist.
        """
        ...

    @abstractmethod
    async def create_secret(
        self,
        name: str,
        value: str | dict[str, Any],
        secret_type: SecretType = SecretType.STRING,
    ) -> SecretMetadata:
        """Create a new secret.

        Args:
            name: Secret name/identifier.
            value: Secret value (string or dict for JSON).
            secret_type: Type of secret.

        Returns:
            SecretMetadata with creation details.
        """
        ...

    @abstractmethod
    async def update_secret(
        self,
        name: str,
        value: str | dict[str, Any],
    ) -> SecretMetadata:
        """Update an existing secret.

        Args:
            name: Secret name/identifier.
            value: New secret value.

        Returns:
            SecretMetadata with update details.

        Raises:
            SecretNotFoundError: If secret does not exist.
        """
        ...

    @abstractmethod
    async def delete_secret(self, name: str, force: bool = False) -> bool:
        """Delete a secret.

        Args:
            name: Secret name/identifier.
            force: Force deletion without recovery option.

        Returns:
            True if deleted successfully.
        """
        ...

    @abstractmethod
    async def rotate_secret(self, name: str) -> SecretMetadata:
        """Rotate a secret.

        Args:
            name: Secret name/identifier.

        Returns:
            SecretMetadata with rotation details.

        Raises:
            SecretNotFoundError: If secret does not exist.
        """
        ...


class LocalSecretsProvider(BaseSecretsProvider):
    """Local in-memory secrets provider for development/testing.

    Stores secrets in memory. Not suitable for production use.

    **Feature: shared-modules-code-review-fixes, Task 1.2**
    **Validates: Requirements 1.2, 1.3, 1.4, 1.5**
    """

    def __init__(self) -> None:
        """Initialize local secrets provider."""
        self._secrets: dict[str, SecretValue] = {}
        self._metadata: dict[str, SecretMetadata] = {}

    async def get_secret(self, name: str, version: str | None = None) -> SecretValue:
        """Get a secret by name.

        Args:
            name: Secret name/identifier.
            version: Optional version (ignored in local provider).

        Returns:
            SecretValue containing the secret data.

        Raises:
            SecretNotFoundError: If secret does not exist.
        """
        if name not in self._secrets:
            raise SecretNotFoundError(name)
        return self._secrets[name]

    async def create_secret(
        self,
        name: str,
        value: str | dict[str, Any],
        secret_type: SecretType = SecretType.STRING,
    ) -> SecretMetadata:
        """Create a new secret.

        Args:
            name: Secret name/identifier.
            value: Secret value.
            secret_type: Type of secret.

        Returns:
            SecretMetadata with creation details.
        """
        now = datetime.now(UTC)
        metadata = SecretMetadata(
            name=name,
            version="1",
            created_at=now,
            updated_at=now,
        )
        self._secrets[name] = SecretValue(
            value=value,
            secret_type=secret_type,
            metadata=metadata,
        )
        self._metadata[name] = metadata
        return metadata

    async def update_secret(
        self,
        name: str,
        value: str | dict[str, Any],
    ) -> SecretMetadata:
        """Update an existing secret.

        Args:
            name: Secret name/identifier.
            value: New secret value.

        Returns:
            SecretMetadata with update details.

        Raises:
            SecretNotFoundError: If secret does not exist.
        """
        if name not in self._secrets:
            raise SecretNotFoundError(name)

        existing = self._secrets[name]
        now = datetime.now(UTC)
        old_metadata = self._metadata[name]

        new_version = str(int(old_metadata.version) + 1)
        metadata = SecretMetadata(
            name=name,
            version=new_version,
            created_at=old_metadata.created_at,
            updated_at=now,
        )

        self._secrets[name] = SecretValue(
            value=value,
            secret_type=existing.secret_type,
            metadata=metadata,
        )
        self._metadata[name] = metadata
        return metadata

    async def delete_secret(self, name: str, force: bool = False) -> bool:
        """Delete a secret.

        Args:
            name: Secret name/identifier.
            force: Force deletion (ignored in local provider).

        Returns:
            True if deleted, False if not found.
        """
        if name in self._secrets:
            del self._secrets[name]
            del self._metadata[name]
            return True
        return False

    async def rotate_secret(self, name: str) -> SecretMetadata:
        """Rotate a secret (generates new version).

        Args:
            name: Secret name/identifier.

        Returns:
            SecretMetadata with rotation details.

        Raises:
            SecretNotFoundError: If secret does not exist.
        """
        if name not in self._secrets:
            raise SecretNotFoundError(name)

        existing = self._secrets[name]
        now = datetime.now(UTC)
        old_metadata = self._metadata[name]

        new_version = str(int(old_metadata.version) + 1)
        metadata = SecretMetadata(
            name=name,
            version=new_version,
            created_at=old_metadata.created_at,
            updated_at=now,
            rotation_enabled=True,
        )

        self._secrets[name] = SecretValue(
            value=existing.value,
            secret_type=existing.secret_type,
            metadata=metadata,
        )
        self._metadata[name] = metadata
        return metadata

    def clear(self) -> None:
        """Clear all secrets (for testing)."""
        self._secrets.clear()
        self._metadata.clear()
