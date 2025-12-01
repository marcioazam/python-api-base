"""File upload models with PEP 695 generics.

**Feature: enterprise-features-2025, Task 6.1: Create file upload models**
**Validates: Requirements 6.8, 6.9, 6.10**
"""

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Protocol


class UploadError(Enum):
    """File upload error types."""

    FILE_TOO_LARGE = "file_too_large"
    INVALID_TYPE = "invalid_type"
    INVALID_EXTENSION = "invalid_extension"
    QUOTA_EXCEEDED = "quota_exceeded"
    VIRUS_DETECTED = "virus_detected"
    STORAGE_ERROR = "storage_error"
    CHECKSUM_MISMATCH = "checksum_mismatch"


@dataclass(frozen=True, slots=True)
class FileMetadata:
    """Metadata for an uploaded file.

    Attributes:
        id: Unique file identifier.
        filename: Original filename.
        content_type: MIME type of the file.
        size_bytes: File size in bytes.
        checksum: SHA-256 checksum of file content.
        uploaded_by: User ID who uploaded the file.
        uploaded_at: When the file was uploaded.
        tenant_id: Tenant the file belongs to.
        storage_key: Key/path in storage backend.
        metadata: Additional custom metadata.
    """

    id: str
    filename: str
    content_type: str
    size_bytes: int
    checksum: str
    uploaded_by: str
    uploaded_at: datetime
    tenant_id: str
    storage_key: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class UploadResult:
    """Result of a successful file upload.

    Attributes:
        file_id: The unique file identifier.
        storage_key: The key/path in storage.
        url: Public or presigned URL to access the file.
        metadata: The file metadata.
    """

    file_id: str
    storage_key: str
    url: str
    metadata: FileMetadata


@dataclass(frozen=True, slots=True)
class FileValidationConfig:
    """Configuration for file validation.

    Attributes:
        max_size_bytes: Maximum allowed file size.
        allowed_types: Set of allowed MIME types.
        allowed_extensions: Set of allowed file extensions.
        scan_for_viruses: Whether to scan for viruses.
    """

    max_size_bytes: int = 10 * 1024 * 1024  # 10MB default
    allowed_types: frozenset[str] = frozenset({
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
        "application/pdf",
        "text/plain",
        "text/csv",
    })
    allowed_extensions: frozenset[str] = frozenset({
        ".jpg", ".jpeg", ".png", ".gif", ".webp",
        ".pdf", ".txt", ".csv",
    })
    scan_for_viruses: bool = False


class StorageProvider[TMetadata](Protocol):
    """Protocol for storage providers with PEP 695 generics.

    Type Parameters:
        TMetadata: The type of metadata associated with stored files.
    """

    async def upload(
        self,
        key: str,
        content: bytes,
        content_type: str,
        metadata: TMetadata,
    ) -> str:
        """Upload a file to storage.

        Args:
            key: Storage key/path for the file.
            content: File content as bytes.
            content_type: MIME type of the file.
            metadata: Metadata to associate with the file.

        Returns:
            The storage URL or key.
        """
        ...

    async def download(self, key: str) -> AsyncIterator[bytes]:
        """Download a file from storage.

        Args:
            key: Storage key/path of the file.

        Yields:
            File content in chunks.
        """
        ...

    async def delete(self, key: str) -> bool:
        """Delete a file from storage.

        Args:
            key: Storage key/path of the file.

        Returns:
            True if file was deleted.
        """
        ...

    async def get_presigned_url(
        self,
        key: str,
        expires_in: int = 3600,
        method: str = "GET",
    ) -> str:
        """Generate a presigned URL for file access.

        Args:
            key: Storage key/path of the file.
            expires_in: URL expiration time in seconds.
            method: HTTP method (GET for download, PUT for upload).

        Returns:
            The presigned URL.
        """
        ...

    async def exists(self, key: str) -> bool:
        """Check if a file exists in storage.

        Args:
            key: Storage key/path of the file.

        Returns:
            True if file exists.
        """
        ...
