"""Dapr secrets management.

This module provides secrets retrieval from configured secret stores.
"""

from core.shared.logging import get_logger
from infrastructure.dapr.client import DaprClientWrapper
from infrastructure.dapr.errors import DaprConnectionError, SecretNotFoundError

logger = get_logger(__name__)


class SecretsManager:
    """Manages secrets operations."""

    def __init__(self, client: DaprClientWrapper, store_name: str) -> None:
        """Initialize the secrets manager.

        Args:
            client: Dapr client wrapper.
            store_name: Default secret store component name.
        """
        self._client = client
        self._store_name = store_name
        self._cache: dict[str, dict[str, str]] = {}

    @property
    def store_name(self) -> str:
        """Get the default secret store name."""
        return self._store_name

    async def get_secret(
        self,
        key: str,
        store_name: str | None = None,
        metadata: dict[str, str] | None = None,
        use_cache: bool = True,
    ) -> str:
        """Get a single secret value.

        Args:
            key: Secret key.
            store_name: Secret store component name.
            metadata: Additional metadata.
            use_cache: Whether to use cached value.

        Returns:
            Secret value.

        Raises:
            SecretNotFoundError: If secret is not found.
        """
        store = store_name or self._store_name
        cache_key = f"{store}:{key}"

        if use_cache and cache_key in self._cache:
            cached = self._cache[cache_key]
            if key in cached:
                return cached[key]

        secrets = await self._client.get_secret(store, key, metadata)

        if key not in secrets:
            raise SecretNotFoundError(
                message=f"Secret key '{key}' not found in response",
                store_name=store,
                secret_name=key,
            )

        self._cache[cache_key] = secrets
        logger.debug("secret_retrieved", store=store, key=key)

        return secrets[key]

    async def get_bulk_secrets(
        self,
        store_name: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> dict[str, dict[str, str]]:
        """Get all secrets from a store.

        Args:
            store_name: Secret store component name.
            metadata: Additional metadata.

        Returns:
            Dictionary of secret names to secret values.
        """
        store = store_name or self._store_name
        url = f"/v1.0/secrets/{store}/bulk"
        headers = {}

        if metadata:
            for k, v in metadata.items():
                headers[f"metadata.{k}"] = v

        try:
            response = await self._client.http_client.get(url, headers=headers)
            response.raise_for_status()
            secrets = response.json()

            for key, value in secrets.items():
                self._cache[f"{store}:{key}"] = value

            logger.debug("bulk_secrets_retrieved", store=store, count=len(secrets))
            return secrets
        except Exception as e:
            raise DaprConnectionError(
                message=f"Failed to get bulk secrets from {store}",
                details={"error": str(e)},
            ) from e

    def clear_cache(self, store_name: str | None = None) -> None:
        """Clear the secrets cache.

        Args:
            store_name: If specified, only clear cache for this store.
        """
        if store_name:
            keys_to_remove = [
                k for k in self._cache if k.startswith(f"{store_name}:")
            ]
            for key in keys_to_remove:
                del self._cache[key]
        else:
            self._cache.clear()

        logger.debug("secrets_cache_cleared", store=store_name or "all")
