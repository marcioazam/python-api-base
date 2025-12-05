"""Dapr state management.

This module provides state store operations with transactional support.
"""

import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Generic, TypeVar

from core.shared.logging import get_logger
from infrastructure.dapr.client import DaprClientWrapper
from infrastructure.dapr.errors import DaprConnectionError, StateNotFoundError

logger = get_logger(__name__)

T = TypeVar("T")


class Consistency(Enum):
    """State consistency levels."""

    EVENTUAL = "eventual"
    STRONG = "strong"


class Concurrency(Enum):
    """State concurrency modes."""

    FIRST_WRITE = "first-write"
    LAST_WRITE = "last-write"


@dataclass
class StateOptions:
    """Options for state operations."""

    consistency: Consistency = Consistency.STRONG
    concurrency: Concurrency = Concurrency.LAST_WRITE


@dataclass
class StateItem(Generic[T]):
    """State item with metadata."""

    key: str
    value: T
    etag: str | None = None
    metadata: dict[str, str] | None = None


class StateManager:
    """Manages state store operations."""

    def __init__(self, client: DaprClientWrapper, store_name: str) -> None:
        """Initialize the state manager.

        Args:
            client: Dapr client wrapper.
            store_name: State store component name.
        """
        self._client = client
        self._store_name = store_name

    @property
    def store_name(self) -> str:
        """Get the state store name."""
        return self._store_name

    async def get(self, key: str) -> StateItem[bytes] | None:
        """Get state by key.

        Args:
            key: State key.

        Returns:
            StateItem if found, None otherwise.
        """
        value, etag = await self._client.get_state(self._store_name, key)
        if value is None:
            return None
        return StateItem(key=key, value=value, etag=etag)

    async def get_bulk(self, keys: list[str]) -> list[StateItem[bytes]]:
        """Get multiple states by keys.

        Args:
            keys: List of state keys.

        Returns:
            List of StateItems for found keys.
        """
        url = f"/v1.0/state/{self._store_name}/bulk"
        headers = {"Content-Type": "application/json"}

        try:
            response = await self._client.http_client.post(
                url,
                content=json.dumps({"keys": keys}),
                headers=headers,
            )
            response.raise_for_status()
            items = response.json()

            result = []
            for item in items:
                if item.get("data"):
                    result.append(
                        StateItem(
                            key=item["key"],
                            value=item["data"].encode()
                            if isinstance(item["data"], str)
                            else item["data"],
                            etag=item.get("etag"),
                        )
                    )
            return result
        except Exception as e:
            raise DaprConnectionError(
                message=f"Failed to get bulk state from {self._store_name}",
                details={"error": str(e)},
            ) from e

    async def save(
        self,
        key: str,
        value: bytes,
        etag: str | None = None,
        options: StateOptions | None = None,
        ttl_seconds: int | None = None,
    ) -> None:
        """Save state.

        Args:
            key: State key.
            value: State value.
            etag: ETag for optimistic concurrency.
            options: State options.
            ttl_seconds: Time-to-live in seconds.
        """
        metadata: dict[str, str] = {}
        if ttl_seconds:
            metadata["ttlInSeconds"] = str(ttl_seconds)
        if options:
            metadata["consistency"] = options.consistency.value
            metadata["concurrency"] = options.concurrency.value

        await self._client.save_state(
            self._store_name,
            key,
            value,
            etag=etag,
            metadata=metadata if metadata else None,
        )

    async def save_bulk(self, items: list[StateItem[bytes]]) -> None:
        """Save multiple states.

        Args:
            items: List of StateItems to save.
        """
        url = f"/v1.0/state/{self._store_name}"
        headers = {"Content-Type": "application/json"}

        state_items = []
        for item in items:
            state_item: dict[str, Any] = {
                "key": item.key,
                "value": item.value.decode()
                if isinstance(item.value, bytes)
                else item.value,
            }
            if item.etag:
                state_item["etag"] = item.etag
            if item.metadata:
                state_item["metadata"] = item.metadata
            state_items.append(state_item)

        try:
            response = await self._client.http_client.post(
                url,
                content=json.dumps(state_items),
                headers=headers,
            )
            response.raise_for_status()
        except Exception as e:
            raise DaprConnectionError(
                message=f"Failed to save bulk state to {self._store_name}",
                details={"error": str(e)},
            ) from e

    async def delete(self, key: str, etag: str | None = None) -> bool:
        """Delete state by key.

        Args:
            key: State key.
            etag: ETag for optimistic concurrency.

        Returns:
            True if deleted, False if not found.
        """
        return await self._client.delete_state(self._store_name, key, etag)

    async def transaction(self, operations: list[dict[str, Any]]) -> None:
        """Execute transactional state operations.

        Args:
            operations: List of operations. Each operation should have:
                - operation: "upsert" or "delete"
                - request: {"key": str, "value": Any (for upsert)}

        Raises:
            DaprConnectionError: If transaction fails.
        """
        url = f"/v1.0/state/{self._store_name}/transaction"
        headers = {"Content-Type": "application/json"}

        try:
            response = await self._client.http_client.post(
                url,
                content=json.dumps({"operations": operations}),
                headers=headers,
            )
            response.raise_for_status()
        except Exception as e:
            raise DaprConnectionError(
                message=f"Transaction failed on {self._store_name}",
                details={"error": str(e)},
            ) from e

    async def query(self, query: dict[str, Any]) -> list[StateItem[bytes]]:
        """Query state store.

        Args:
            query: Query object with filter, sort, page, etc.

        Returns:
            List of matching StateItems.

        Note:
            Query API is only supported by certain state stores.
        """
        url = f"/v1.0-alpha1/state/{self._store_name}/query"
        headers = {"Content-Type": "application/json"}

        try:
            response = await self._client.http_client.post(
                url,
                content=json.dumps(query),
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()

            result = []
            for item in data.get("results", []):
                result.append(
                    StateItem(
                        key=item["key"],
                        value=json.dumps(item["data"]).encode(),
                        etag=item.get("etag"),
                    )
                )
            return result
        except Exception as e:
            raise DaprConnectionError(
                message=f"Query failed on {self._store_name}",
                details={"error": str(e)},
            ) from e
