"""High-level secrets manager.

**Feature: code-review-refactoring, Task 18.1: Refactor secrets_manager.py**
**Validates: Requirements 5.7**

**Feature: shared-modules-code-review-fixes, Task 2.1, 2.2, 2.3**
**Validates: Requirements 2.1, 2.2, 2.3**
"""

import asyncio
import json
import logging
from typing import Any

_logger = logging.getLogger(__name__)

from .enums import SecretType
from .exceptions import SecretNotFoundError
from .models import RotationConfig, SecretMetadata, SecretValue
from .providers import BaseSecretsProvider


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
        """Initialize secrets manager."""
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
        """
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

    async def get_secret_json(
        self, name: str, version: str | None = None
    ) -> dict[str, Any]:
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
        """Schedule automatic secret rotation."""
        if name in self._rotation_tasks:
            self._rotation_tasks[name].cancel()

        async def rotation_loop() -> None:
            while True:
                await asyncio.sleep(interval_seconds)
                try:
                    await self.rotate_secret(name)
                    _logger.info(
                        "Secret rotated successfully",
                        extra={"secret_name": name},
                    )
                except Exception:
                    _logger.exception(
                        "Secret rotation failed",
                        extra={"secret_name": name},
                    )

        task = asyncio.create_task(rotation_loop())
        self._rotation_tasks[name] = task

    def cancel_rotation(self, name: str) -> bool:
        """Cancel scheduled rotation."""
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
