"""Idempotency key support for API requests.

Stores responses for requests with Idempotency-Key header
and returns cached responses for duplicate requests.
"""

import hashlib
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any, Protocol

from pydantic import BaseModel


class IdempotencyStorage(Protocol):
    """Protocol for idempotency storage backends."""

    async def get(self, key: str) -> dict[str, Any] | None:
        """Get stored response by key."""
        ...

    async def set(
        self,
        key: str,
        value: dict[str, Any],
        ttl: int,
    ) -> None:
        """Store response with TTL."""
        ...

    async def delete(self, key: str) -> bool:
        """Delete stored response."""
        ...

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        ...


@dataclass
class IdempotencyRecord:
    """Record of an idempotent request."""

    key: str
    request_hash: str
    status_code: int
    response_body: dict[str, Any] | None
    response_headers: dict[str, str]
    created_at: datetime
    expires_at: datetime

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "key": self.key,
            "request_hash": self.request_hash,
            "status_code": self.status_code,
            "response_body": self.response_body,
            "response_headers": self.response_headers,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "IdempotencyRecord":
        """Create from dictionary."""
        return cls(
            key=data["key"],
            request_hash=data["request_hash"],
            status_code=data["status_code"],
            response_body=data.get("response_body"),
            response_headers=data.get("response_headers", {}),
            created_at=datetime.fromisoformat(data["created_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"]),
        )


class IdempotencyConflictError(Exception):
    """Raised when request hash doesn't match stored request."""

    def __init__(self, key: str) -> None:
        self.key = key
        super().__init__(
            f"Idempotency key '{key}' was used with different request parameters"
        )


class IdempotencyInProgressError(Exception):
    """Raised when a request with the same key is in progress."""

    def __init__(self, key: str) -> None:
        self.key = key
        super().__init__(
            f"Request with idempotency key '{key}' is already in progress"
        )


class InMemoryIdempotencyStorage:
    """In-memory storage for idempotency records.

    Suitable for development and single-instance deployments.
    For production, use Redis or database storage.
    """

    def __init__(self) -> None:
        self._store: dict[str, dict[str, Any]] = {}
        self._locks: set[str] = set()

    async def get(self, key: str) -> dict[str, Any] | None:
        """Get stored response by key."""
        record = self._store.get(key)
        if record is None:
            return None

        # Check expiration
        expires_at = datetime.fromisoformat(record["expires_at"])
        if datetime.now(tz=UTC) > expires_at:
            del self._store[key]
            return None

        return record

    async def set(
        self,
        key: str,
        value: dict[str, Any],
        ttl: int,
    ) -> None:
        """Store response with TTL."""
        self._store[key] = value

    async def delete(self, key: str) -> bool:
        """Delete stored response."""
        if key in self._store:
            del self._store[key]
            return True
        return False

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        return key in self._store

    async def acquire_lock(self, key: str) -> bool:
        """Acquire processing lock for key."""
        if key in self._locks:
            return False
        self._locks.add(key)
        return True

    async def release_lock(self, key: str) -> None:
        """Release processing lock for key."""
        self._locks.discard(key)


class IdempotencyService:
    """Service for handling idempotent requests.

    Stores responses for requests with Idempotency-Key header
    and returns cached responses for duplicate requests.

    Example:
        >>> service = IdempotencyService(storage=InMemoryIdempotencyStorage())
        >>> 
        >>> # Check for existing response
        >>> existing = await service.get_response(key, request_hash)
        >>> if existing:
        ...     return existing
        >>> 
        >>> # Process request and store response
        >>> response = await process_request()
        >>> await service.store_response(key, request_hash, response)
    """

    def __init__(
        self,
        storage: IdempotencyStorage,
        ttl: int = 86400,  # 24 hours default
        lock_timeout: int = 30,  # 30 seconds lock timeout
    ) -> None:
        """Initialize idempotency service.

        Args:
            storage: Storage backend for idempotency records.
            ttl: Time-to-live for stored responses in seconds.
            lock_timeout: Timeout for request processing locks.
        """
        self._storage = storage
        self._ttl = ttl
        self._lock_timeout = lock_timeout

    def compute_request_hash(
        self,
        method: str,
        path: str,
        body: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> str:
        """Compute hash of request for conflict detection.

        Args:
            method: HTTP method.
            path: Request path.
            body: Request body.
            headers: Relevant headers to include in hash.

        Returns:
            SHA-256 hash of request.
        """
        hash_input = f"{method}:{path}"

        if body:
            hash_input += f":{body.decode('utf-8', errors='ignore')}"

        if headers:
            # Include specific headers in hash
            relevant_headers = ["content-type", "accept"]
            for header in relevant_headers:
                if header in headers:
                    hash_input += f":{header}={headers[header]}"

        return hashlib.sha256(hash_input.encode()).hexdigest()

    async def get_response(
        self,
        idempotency_key: str,
        request_hash: str,
    ) -> IdempotencyRecord | None:
        """Get stored response for idempotency key.

        Args:
            idempotency_key: The idempotency key from request header.
            request_hash: Hash of the current request.

        Returns:
            Stored response if exists and matches, None otherwise.

        Raises:
            IdempotencyConflictError: If key exists but request hash differs.
        """
        record_data = await self._storage.get(idempotency_key)
        if record_data is None:
            return None

        record = IdempotencyRecord.from_dict(record_data)

        # Verify request hash matches
        if record.request_hash != request_hash:
            raise IdempotencyConflictError(idempotency_key)

        return record

    async def store_response(
        self,
        idempotency_key: str,
        request_hash: str,
        status_code: int,
        response_body: dict[str, Any] | None = None,
        response_headers: dict[str, str] | None = None,
    ) -> IdempotencyRecord:
        """Store response for idempotency key.

        Args:
            idempotency_key: The idempotency key from request header.
            request_hash: Hash of the request.
            status_code: HTTP status code of response.
            response_body: Response body.
            response_headers: Response headers to store.

        Returns:
            Created idempotency record.
        """
        now = datetime.now(tz=UTC)
        record = IdempotencyRecord(
            key=idempotency_key,
            request_hash=request_hash,
            status_code=status_code,
            response_body=response_body,
            response_headers=response_headers or {},
            created_at=now,
            expires_at=datetime.fromtimestamp(now.timestamp() + self._ttl, tz=UTC),
        )

        await self._storage.set(
            idempotency_key,
            record.to_dict(),
            self._ttl,
        )

        return record

    async def delete_response(self, idempotency_key: str) -> bool:
        """Delete stored response.

        Args:
            idempotency_key: The idempotency key.

        Returns:
            True if deleted, False if not found.
        """
        return await self._storage.delete(idempotency_key)

    async def acquire_lock(self, idempotency_key: str) -> bool:
        """Acquire processing lock for idempotency key.

        Args:
            idempotency_key: The idempotency key.

        Returns:
            True if lock acquired, False if already locked.
        """
        if hasattr(self._storage, "acquire_lock"):
            return await self._storage.acquire_lock(idempotency_key)
        return True

    async def release_lock(self, idempotency_key: str) -> None:
        """Release processing lock for idempotency key.

        Args:
            idempotency_key: The idempotency key.
        """
        if hasattr(self._storage, "release_lock"):
            await self._storage.release_lock(idempotency_key)


def create_idempotency_service(
    storage: IdempotencyStorage | None = None,
    ttl: int = 86400,
) -> IdempotencyService:
    """Factory function to create idempotency service.

    Args:
        storage: Storage backend. Uses in-memory if not provided.
        ttl: Time-to-live for stored responses.

    Returns:
        Configured IdempotencyService.
    """
    if storage is None:
        storage = InMemoryIdempotencyStorage()

    return IdempotencyService(storage=storage, ttl=ttl)
