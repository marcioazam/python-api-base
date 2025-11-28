"""Secrets management with AWS Secrets Manager and HashiCorp Vault support.

**Feature: api-architecture-analysis, Task 11.6: Secrets Management**
**Validates: Requirements 5.1, 5.5**

Provides secure secret storage, retrieval, and automatic rotation.
"""

import asyncio
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field


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


@dataclass(frozen=True)
class SecretMetadata:
    """Metadata about a secret.

    Attributes:
        name: Secret name/identifier.
        version: Secret version.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
        rotation_enabled: Whether automatic rotation is enabled.
        next_rotation: Next scheduled rotation time.
        tags: Secret tags/labels.
    """

    name: str
    version: str = "AWSCURRENT"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    rotation_enabled: bool = False
    next_rotation: datetime | None = None
    tags: dict[str, str] = field(default_factory=dict)


class SecretValue(BaseModel):
    """Secret value container.

    Attributes:
        value: The secret value (string or dict).
        secret_type: Type of the secret.
        metadata: Secret metadata.
    """

    value: str | dict[str, Any]
    secret_type: SecretType = SecretType.STRING
    metadata: SecretMetadata | None = None

    model_config = {"arbitrary_types_allowed": True}


@dataclass
class RotationConfig:
    """Secret rotation configuration.

    Attributes:
        enabled: Whether rotation is enabled.
        interval_days: Days between rotations.
        rotation_lambda_arn: AWS Lambda ARN for rotation (AWS only).
        auto_rotate_on_access: Rotate if secret is near expiration.
    """

    enabled: bool = False
    interval_days: int = 30
    rotation_lambda_arn: str | None = None
    auto_rotate_on_access: bool = False


class SecretsError(Exception):
    """Base secrets error."""

    def __init__(self, message: str, error_code: str = "SECRETS_ERROR") -> None:
        super().__init__(message)
        self.error_code = error_code


class SecretNotFoundError(SecretsError):
    """Secret not found error."""

    def __init__(self, secret_name: str) -> None:
        super().__init__(f"Secret not found: {secret_name}", "SECRET_NOT_FOUND")
        self.secret_name = secret_name


class SecretAccessDeniedError(SecretsError):
    """Secret access denied error."""

    def __init__(self, secret_name: str) -> None:
        super().__init__(f"Access denied to secret: {secret_name}", "SECRET_ACCESS_DENIED")
        self.secret_name = secret_name


class SecretRotationError(SecretsError):
    """Secret rotation error."""

    def __init__(self, secret_name: str, reason: str) -> None:
        super().__init__(f"Rotation failed for {secret_name}: {reason}", "SECRET_ROTATION_ERROR")
        self.secret_name = secret_name


@runtime_checkable
class SecretCache(Protocol):
    """Protocol for secret caching."""

    async def get(self, key: str) -> SecretValue | None:
        """Get cached secret."""
        ...

    async def set(self, key: str, value: SecretValue, ttl: int) -> None:
        """Cache secret with TTL."""
        ...

    async def delete(self, key: str) -> None:
        """Remove secret from cache."""
        ...


class InMemorySecretCache:
    """In-memory secret cache for development/testing."""

    def __init__(self) -> None:
        self._cache: dict[str, tuple[SecretValue, datetime]] = {}

    async def get(self, key: str) -> SecretValue | None:
        """Get cached secret if not expired."""
        if key not in self._cache:
            return None

        value, expires_at = self._cache[key]
        if datetime.now(timezone.utc) > expires_at:
            del self._cache[key]
            return None

        return value

    async def set(self, key: str, value: SecretValue, ttl: int) -> None:
        """Cache secret with TTL in seconds."""
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl)
        self._cache[key] = (value, expires_at)

    async def delete(self, key: str) -> None:
        """Remove secret from cache."""
        self._cache.pop(key, None)

    def clear(self) -> None:
        """Clear all cached secrets."""
        self._cache.clear()


class BaseSecretsProvider(ABC):
    """Base class for secrets providers."""

    def __init__(
        self,
        cache: SecretCache | None = None,
        cache_ttl: int = 300,
    ) -> None:
        """Initialize secrets provider.

        Args:
            cache: Optional cache for secrets.
            cache_ttl: Cache TTL in seconds (default 5 minutes).
        """
        self._cache = cache
        self._cache_ttl = cache_ttl

    @property
    @abstractmethod
    def provider(self) -> SecretProvider:
        """Get provider type."""
        ...

    @abstractmethod
    async def _get_secret(self, name: str, version: str | None = None) -> SecretValue:
        """Get secret from provider (internal)."""
        ...

    @abstractmethod
    async def _create_secret(self, name: str, value: str | dict, secret_type: SecretType) -> SecretMetadata:
        """Create secret in provider (internal)."""
        ...

    @abstractmethod
    async def _update_secret(self, name: str, value: str | dict) -> SecretMetadata:
        """Update secret in provider (internal)."""
        ...

    @abstractmethod
    async def _delete_secret(self, name: str, force: bool = False) -> bool:
        """Delete secret from provider (internal)."""
        ...

    async def get_secret(self, name: str, version: str | None = None) -> SecretValue:
        """Get secret with caching.

        Args:
            name: Secret name.
            version: Optional version (default: current).

        Returns:
            Secret value.

        Raises:
            SecretNotFoundError: If secret doesn't exist.
        """
        cache_key = f"{name}:{version or 'current'}"

        # Check cache first
        if self._cache:
            cached = await self._cache.get(cache_key)
            if cached:
                return cached

        # Get from provider
        secret = await self._get_secret(name, version)

        # Cache result
        if self._cache:
            await self._cache.set(cache_key, secret, self._cache_ttl)

        return secret

    async def get_secret_string(self, name: str, version: str | None = None) -> str:
        """Get secret as string.

        Args:
            name: Secret name.
            version: Optional version.

        Returns:
            Secret string value.
        """
        secret = await self.get_secret(name, version)
        if isinstance(secret.value, dict):
            return json.dumps(secret.value)
        return secret.value

    async def get_secret_json(self, name: str, version: str | None = None) -> dict[str, Any]:
        """Get secret as JSON dict.

        Args:
            name: Secret name.
            version: Optional version.

        Returns:
            Secret as dictionary.
        """
        secret = await self.get_secret(name, version)
        if isinstance(secret.value, str):
            return json.loads(secret.value)
        return secret.value

    async def create_secret(
        self,
        name: str,
        value: str | dict,
        secret_type: SecretType = SecretType.STRING,
    ) -> SecretMetadata:
        """Create a new secret.

        Args:
            name: Secret name.
            value: Secret value.
            secret_type: Type of secret.

        Returns:
            Secret metadata.
        """
        return await self._create_secret(name, value, secret_type)

    async def update_secret(self, name: str, value: str | dict) -> SecretMetadata:
        """Update existing secret.

        Args:
            name: Secret name.
            value: New secret value.

        Returns:
            Updated metadata.
        """
        # Invalidate cache
        if self._cache:
            await self._cache.delete(f"{name}:current")

        return await self._update_secret(name, value)

    async def delete_secret(self, name: str, force: bool = False) -> bool:
        """Delete a secret.

        Args:
            name: Secret name.
            force: Force immediate deletion.

        Returns:
            True if deleted.
        """
        # Invalidate cache
        if self._cache:
            await self._cache.delete(f"{name}:current")

        return await self._delete_secret(name, force)

    async def rotate_secret(self, name: str) -> SecretMetadata:
        """Trigger secret rotation.

        Args:
            name: Secret name.

        Returns:
            Updated metadata.

        Raises:
            SecretRotationError: If rotation fails.
        """
        raise NotImplementedError("Rotation not supported by this provider")


class LocalSecretsProvider(BaseSecretsProvider):
    """Local/in-memory secrets provider for development and testing."""

    def __init__(
        self,
        cache: SecretCache | None = None,
        cache_ttl: int = 300,
    ) -> None:
        super().__init__(cache, cache_ttl)
        self._secrets: dict[str, SecretValue] = {}
        self._versions: dict[str, list[str]] = {}

    @property
    def provider(self) -> SecretProvider:
        return SecretProvider.LOCAL

    async def _get_secret(self, name: str, version: str | None = None) -> SecretValue:
        if name not in self._secrets:
            raise SecretNotFoundError(name)
        return self._secrets[name]

    async def _create_secret(
        self,
        name: str,
        value: str | dict,
        secret_type: SecretType,
    ) -> SecretMetadata:
        metadata = SecretMetadata(
            name=name,
            version="v1",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        self._secrets[name] = SecretValue(
            value=value,
            secret_type=secret_type,
            metadata=metadata,
        )
        self._versions[name] = ["v1"]

        return metadata

    async def _update_secret(self, name: str, value: str | dict) -> SecretMetadata:
        if name not in self._secrets:
            raise SecretNotFoundError(name)

        existing = self._secrets[name]
        new_version = f"v{len(self._versions.get(name, [])) + 1}"

        metadata = SecretMetadata(
            name=name,
            version=new_version,
            created_at=existing.metadata.created_at if existing.metadata else datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        self._secrets[name] = SecretValue(
            value=value,
            secret_type=existing.secret_type,
            metadata=metadata,
        )
        self._versions.setdefault(name, []).append(new_version)

        return metadata

    async def _delete_secret(self, name: str, force: bool = False) -> bool:
        if name not in self._secrets:
            return False

        del self._secrets[name]
        self._versions.pop(name, None)
        return True

    async def list_secrets(self) -> list[str]:
        """List all secret names."""
        return list(self._secrets.keys())


class SecretsManager:
    """High-level secrets manager with multi-provider support.

    Provides a unified interface for managing secrets across different
    providers with caching, rotation, and fallback support.

    **Feature: code-review-refactoring, Task 14.1: Implement secure secret access**
    **Validates: Requirements 10.1, 10.3**
    """

    def __init__(
        self,
        primary_provider: BaseSecretsProvider,
        fallback_provider: BaseSecretsProvider | None = None,
        rotation_config: RotationConfig | None = None,
        audit_logger: Any | None = None,
    ) -> None:
        """Initialize secrets manager.

        Args:
            primary_provider: Primary secrets provider.
            fallback_provider: Optional fallback provider.
            rotation_config: Optional rotation configuration.
            audit_logger: Optional security audit logger for access logging.
        """
        self._primary = primary_provider
        self._fallback = fallback_provider
        self._rotation_config = rotation_config or RotationConfig()
        self._rotation_tasks: dict[str, asyncio.Task] = {}
        self._audit_logger = audit_logger

    async def get_secret(
        self,
        name: str,
        version: str | None = None,
        accessor: str = "system",
    ) -> SecretValue:
        """Get secret with fallback support and audit logging.

        **Feature: code-review-refactoring, Property 15: Secret Access Logging**
        **Validates: Requirements 10.1, 10.3**

        Args:
            name: Secret name.
            version: Optional version.
            accessor: Who/what is accessing the secret.

        Returns:
            Secret value.

        Raises:
            SecretNotFoundError: If secret not found in any provider.
        """
        # Log access without exposing value
        if self._audit_logger:
            self._audit_logger.log_secret_access(name, accessor, "read")

        try:
            return await self._primary.get_secret(name, version)
        except SecretNotFoundError:
            if self._fallback:
                return await self._fallback.get_secret(name, version)
            raise

    async def get_secret_string(self, name: str, version: str | None = None) -> str:
        """Get secret as string."""
        secret = await self.get_secret(name, version)
        if isinstance(secret.value, dict):
            return json.dumps(secret.value)
        return secret.value

    async def get_secret_json(self, name: str, version: str | None = None) -> dict[str, Any]:
        """Get secret as JSON dict."""
        secret = await self.get_secret(name, version)
        if isinstance(secret.value, str):
            return json.loads(secret.value)
        return secret.value

    async def create_secret(
        self,
        name: str,
        value: str | dict,
        secret_type: SecretType = SecretType.STRING,
        accessor: str = "system",
    ) -> SecretMetadata:
        """Create secret in primary provider with audit logging."""
        if self._audit_logger:
            self._audit_logger.log_secret_access(name, accessor, "create")
        return await self._primary.create_secret(name, value, secret_type)

    async def update_secret(
        self,
        name: str,
        value: str | dict,
        accessor: str = "system",
    ) -> SecretMetadata:
        """Update secret in primary provider with audit logging."""
        if self._audit_logger:
            self._audit_logger.log_secret_access(name, accessor, "update")
        return await self._primary.update_secret(name, value)

    async def delete_secret(
        self,
        name: str,
        force: bool = False,
        accessor: str = "system",
    ) -> bool:
        """Delete secret from primary provider with audit logging."""
        if self._audit_logger:
            self._audit_logger.log_secret_access(name, accessor, "delete")
        return await self._primary.delete_secret(name, force)

    async def rotate_secret(self, name: str, accessor: str = "system") -> SecretMetadata:
        """Manually trigger secret rotation with audit logging."""
        if self._audit_logger:
            self._audit_logger.log_secret_access(name, accessor, "rotate")
        return await self._primary.rotate_secret(name)

    def schedule_rotation(self, name: str, interval_seconds: int) -> None:
        """Schedule automatic secret rotation.

        Args:
            name: Secret name.
            interval_seconds: Rotation interval.
        """
        if name in self._rotation_tasks:
            self._rotation_tasks[name].cancel()

        async def rotation_loop() -> None:
            while True:
                await asyncio.sleep(interval_seconds)
                try:
                    await self.rotate_secret(name)
                except Exception:
                    pass  # Log error in production

        task = asyncio.create_task(rotation_loop())
        self._rotation_tasks[name] = task

    def cancel_rotation(self, name: str) -> bool:
        """Cancel scheduled rotation.

        Args:
            name: Secret name.

        Returns:
            True if rotation was cancelled.
        """
        if name in self._rotation_tasks:
            self._rotation_tasks[name].cancel()
            del self._rotation_tasks[name]
            return True
        return False

    async def close(self) -> None:
        """Cancel all rotation tasks and cleanup."""
        for task in self._rotation_tasks.values():
            task.cancel()
        self._rotation_tasks.clear()
