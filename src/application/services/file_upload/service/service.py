"""File upload service implementation.

**Feature: enterprise-features-2025, Tasks 6.2, 6.5**
**Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.7**
"""

import logging
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

from application.services.file_upload.models import (
    FileMetadata,
    FileValidationConfig,
    StorageProvider,
    UploadError,
    UploadResult,
)
from application.services.file_upload.validators import (
    get_safe_filename,
    validate_file,
)
from core.base.patterns.result import Err, Ok, Result

logger = logging.getLogger(__name__)


class InMemoryStorageProvider:
    """In-memory storage provider for testing."""

    def __init__(self) -> None:
        self._storage: dict[str, tuple[bytes, str, dict[str, Any]]] = {}

    async def upload(
        self,
        key: str,
        content: bytes,
        content_type: str,
        metadata: dict[str, Any],
    ) -> str:
        """Upload to in-memory storage."""
        self._storage[key] = (content, content_type, metadata)
        return f"memory://{key}"

    async def download(self, key: str) -> AsyncIterator[bytes]:
        """Download from in-memory storage."""
        if key in self._storage:
            content, _, _ = self._storage[key]
            yield content

    async def delete(self, key: str) -> bool:
        """Delete from in-memory storage."""
        if key in self._storage:
            del self._storage[key]
            return True
        return False

    async def get_presigned_url(
        self,
        key: str,
        expires_in: int = 3600,
        method: str = "GET",
    ) -> str:
        """Generate mock presigned URL."""
        return f"memory://{key}?expires={expires_in}&method={method}"

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        return key in self._storage


class FileUploadService[TMetadata]:
    """Service for managing file uploads.

    Type Parameters:
        TMetadata: The type of metadata for stored files.
    """

    def __init__(
        self,
        storage: StorageProvider[TMetadata],
        config: FileValidationConfig | None = None,
    ) -> None:
        """Initialize file upload service.

        Args:
            storage: Storage provider implementation.
            config: File validation configuration.
        """
        self._storage = storage
        self._config = config or FileValidationConfig()
        self._quotas: dict[str, int] = {}  # tenant_id -> used bytes
        self._quota_limits: dict[str, int] = {}  # tenant_id -> max bytes

    def set_quota(self, tenant_id: str, max_bytes: int) -> None:
        """Set storage quota for a tenant.

        Args:
            tenant_id: The tenant identifier.
            max_bytes: Maximum storage in bytes.
        """
        self._quota_limits[tenant_id] = max_bytes
        if tenant_id not in self._quotas:
            self._quotas[tenant_id] = 0

    def get_quota_usage(self, tenant_id: str) -> tuple[int, int]:
        """Get quota usage for a tenant.

        Args:
            tenant_id: The tenant identifier.

        Returns:
            Tuple of (used_bytes, max_bytes).
        """
        used = self._quotas.get(tenant_id, 0)
        limit = self._quota_limits.get(tenant_id, 0)
        return used, limit

    async def upload(
        self,
        filename: str,
        content: bytes,
        content_type: str,
        user_id: str,
        tenant_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> Result[UploadResult, UploadError]:
        """Upload a file.

        Args:
            filename: Original filename.
            content: File content.
            content_type: MIME type.
            user_id: Uploading user ID.
            tenant_id: Tenant ID.
            metadata: Additional metadata.

        Returns:
            Result with UploadResult on success or UploadError on failure.
        """
        # Validate file
        validation = validate_file(filename, content, content_type, self._config)
        if validation.is_err():
            return Err(validation.unwrap_err())

        checksum = validation.unwrap()

        # Check quota
        if tenant_id in self._quota_limits:
            used = self._quotas.get(tenant_id, 0)
            limit = self._quota_limits[tenant_id]
            if used + len(content) > limit:
                return Err(UploadError.QUOTA_EXCEEDED)

        # Generate storage key
        file_id = str(uuid.uuid4())
        safe_filename = get_safe_filename(filename)
        storage_key = f"{tenant_id}/{file_id}/{safe_filename}"

        # Create metadata
        file_metadata = FileMetadata(
            id=file_id,
            filename=safe_filename,
            content_type=content_type,
            size_bytes=len(content),
            checksum=checksum,
            uploaded_by=user_id,
            uploaded_at=datetime.now(UTC),
            tenant_id=tenant_id,
            storage_key=storage_key,
            metadata=metadata or {},
        )

        try:
            # Upload to storage
            url = await self._storage.upload(
                storage_key,
                content,
                content_type,
                metadata or {},  # type: ignore
            )

            # Update quota
            if tenant_id in self._quotas:
                self._quotas[tenant_id] += len(content)
            else:
                self._quotas[tenant_id] = len(content)

            return Ok(
                UploadResult(
                    file_id=file_id,
                    storage_key=storage_key,
                    url=url,
                    metadata=file_metadata,
                )
            )

        except Exception as e:
            logger.error(f"Storage upload failed: {e}")
            return Err(UploadError.STORAGE_ERROR)

    async def download(self, storage_key: str) -> AsyncIterator[bytes]:
        """Download a file.

        Args:
            storage_key: The storage key of the file.

        Yields:
            File content in chunks.
        """
        async for chunk in self._storage.download(storage_key):
            yield chunk

    async def delete(
        self,
        storage_key: str,
        tenant_id: str,
        file_size: int,
    ) -> bool:
        """Delete a file.

        Args:
            storage_key: The storage key of the file.
            tenant_id: The tenant ID.
            file_size: Size of the file being deleted.

        Returns:
            True if file was deleted.
        """
        result = await self._storage.delete(storage_key)
        if result and tenant_id in self._quotas:
            self._quotas[tenant_id] = max(0, self._quotas[tenant_id] - file_size)
        return result

    async def get_presigned_url(
        self,
        storage_key: str,
        expires_in: int = 3600,
        method: str = "GET",
    ) -> str:
        """Get a presigned URL for file access.

        Args:
            storage_key: The storage key of the file.
            expires_in: URL expiration in seconds.
            method: HTTP method (GET or PUT).

        Returns:
            The presigned URL.
        """
        return await self._storage.get_presigned_url(storage_key, expires_in, method)

    async def exists(self, storage_key: str) -> bool:
        """Check if a file exists.

        Args:
            storage_key: The storage key of the file.

        Returns:
            True if file exists.
        """
        return await self._storage.exists(storage_key)
