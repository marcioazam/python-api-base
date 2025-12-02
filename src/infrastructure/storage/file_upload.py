"""Generic file upload handling with PEP 695 type parameters.

**Feature: python-api-base-2025-generics-audit**
**Validates: Requirements 17.1, 17.2, 17.3, 17.4, 17.5**
"""

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel

from core.base.result import Err, Ok, Result


@dataclass(frozen=True, slots=True)
class FileInfo:
    """File information metadata."""

    filename: str
    content_type: str
    size_bytes: int
    checksum: str | None = None


@dataclass(frozen=True, slots=True)
class UploadProgress:
    """Upload progress tracking."""

    bytes_uploaded: int
    total_bytes: int
    chunks_completed: int
    total_chunks: int

    @property
    def percentage(self) -> float:
        """Get upload percentage."""
        if self.total_bytes == 0:
            return 0.0
        return (self.bytes_uploaded / self.total_bytes) * 100


@runtime_checkable
class FileValidator[T](Protocol):
    """Generic file validator protocol.

    Type Parameters:
        T: Validation context type.

    **Feature: python-api-base-2025-generics-audit**
    **Validates: Requirements 17.2**
    """

    def validate(
        self,
        file_info: FileInfo,
        context: T | None = None,
    ) -> Result[FileInfo, str]:
        """Validate file against rules.

        Args:
            file_info: File metadata to validate.
            context: Optional validation context.

        Returns:
            Ok with file_info if valid, Err with message if invalid.
        """
        ...


@dataclass
class FileValidationRules:
    """Configurable file validation rules."""

    allowed_extensions: set[str] = field(default_factory=set)
    allowed_content_types: set[str] = field(default_factory=set)
    max_size_bytes: int = 10 * 1024 * 1024  # 10MB
    min_size_bytes: int = 1


class ConfigurableFileValidator[T]:
    """Configurable file validator with typed context.

    **Feature: python-api-base-2025-generics-audit**
    **Validates: Requirements 17.2**
    """

    def __init__(self, rules: FileValidationRules) -> None:
        self._rules = rules

    def validate(
        self,
        file_info: FileInfo,
        context: T | None = None,
    ) -> Result[FileInfo, str]:
        """Validate file against configured rules."""
        # Check size
        if file_info.size_bytes < self._rules.min_size_bytes:
            return Err(f"File too small: {file_info.size_bytes} bytes")
        if file_info.size_bytes > self._rules.max_size_bytes:
            return Err(f"File too large: {file_info.size_bytes} bytes")

        # Check extension
        if self._rules.allowed_extensions:
            ext = file_info.filename.rsplit(".", 1)[-1].lower()
            if ext not in self._rules.allowed_extensions:
                return Err(f"Extension not allowed: {ext}")

        # Check content type
        if self._rules.allowed_content_types:
            if file_info.content_type not in self._rules.allowed_content_types:
                return Err(f"Content type not allowed: {file_info.content_type}")

        return Ok(file_info)


@runtime_checkable
class FileStorage[TProvider](Protocol):
    """Generic file storage protocol for multiple backends.

    Type Parameters:
        TProvider: Provider-specific configuration type.

    **Feature: python-api-base-2025-generics-audit**
    **Validates: Requirements 17.3**
    """

    async def upload(
        self,
        key: str,
        data: bytes | AsyncIterator[bytes],
        content_type: str,
    ) -> Result[str, Exception]:
        """Upload file to storage.

        Args:
            key: Storage key/path.
            data: File data or async stream.
            content_type: MIME type.

        Returns:
            Ok with storage URL or Err with exception.
        """
        ...

    async def download(self, key: str) -> Result[bytes, Exception]:
        """Download file from storage.

        Args:
            key: Storage key/path.

        Returns:
            Ok with file bytes or Err with exception.
        """
        ...

    async def delete(self, key: str) -> Result[bool, Exception]:
        """Delete file from storage.

        Args:
            key: Storage key/path.

        Returns:
            Ok with True if deleted, Err with exception.
        """
        ...

    async def exists(self, key: str) -> bool:
        """Check if file exists in storage."""
        ...

    async def generate_signed_url(
        self,
        key: str,
        expiration: timedelta,
        operation: str = "GET",
    ) -> Result[str, Exception]:
        """Generate signed URL for file access.

        **Validates: Requirements 17.5**

        Args:
            key: Storage key/path.
            expiration: URL expiration time.
            operation: HTTP operation (GET, PUT).

        Returns:
            Ok with signed URL or Err with exception.
        """
        ...


@dataclass
class ChunkInfo:
    """Chunk information for resumable uploads."""

    chunk_number: int
    total_chunks: int
    chunk_size: int
    offset: int


class FileUploadHandler[TMetadata: BaseModel]:
    """Generic file upload handler with streaming support.

    Type Parameters:
        TMetadata: User-defined metadata type for uploads.

    **Feature: python-api-base-2025-generics-audit**
    **Validates: Requirements 17.1, 17.4**
    """

    def __init__(
        self,
        storage: FileStorage[Any],
        validator: FileValidator[TMetadata] | None = None,
        chunk_size: int = 1024 * 1024,  # 1MB chunks
    ) -> None:
        self._storage = storage
        self._validator = validator
        self._chunk_size = chunk_size
        self._uploads: dict[str, UploadProgress] = {}

    async def upload(
        self,
        upload_id: str,
        file_info: FileInfo,
        data: bytes | AsyncIterator[bytes],
        metadata: TMetadata | None = None,
    ) -> Result[str, str]:
        """Upload file with optional metadata.

        Args:
            upload_id: Unique upload identifier.
            file_info: File information.
            data: File data or async stream.
            metadata: Optional typed metadata.

        Returns:
            Ok with storage URL or Err with error message.
        """
        # Validate if validator provided
        if self._validator:
            validation = self._validator.validate(file_info, metadata)
            if validation.is_err():
                return Err(validation.error)

        # Upload to storage
        key = f"uploads/{upload_id}/{file_info.filename}"
        result = await self._storage.upload(key, data, file_info.content_type)

        if result.is_err():
            return Err(str(result.error))

        return Ok(result.unwrap())

    async def upload_chunk(
        self,
        upload_id: str,
        chunk: bytes,
        chunk_info: ChunkInfo,
    ) -> Result[UploadProgress, str]:
        """Upload a single chunk for resumable upload.

        **Validates: Requirements 17.4**

        Args:
            upload_id: Unique upload identifier.
            chunk: Chunk data.
            chunk_info: Chunk metadata.

        Returns:
            Ok with progress or Err with error message.
        """
        key = f"chunks/{upload_id}/{chunk_info.chunk_number}"
        result = await self._storage.upload(key, chunk, "application/octet-stream")

        if result.is_err():
            return Err(str(result.error))

        # Update progress
        progress = self._uploads.get(upload_id)
        if progress:
            new_progress = UploadProgress(
                bytes_uploaded=progress.bytes_uploaded + len(chunk),
                total_bytes=progress.total_bytes,
                chunks_completed=progress.chunks_completed + 1,
                total_chunks=chunk_info.total_chunks,
            )
        else:
            new_progress = UploadProgress(
                bytes_uploaded=len(chunk),
                total_bytes=chunk_info.chunk_size * chunk_info.total_chunks,
                chunks_completed=1,
                total_chunks=chunk_info.total_chunks,
            )

        self._uploads[upload_id] = new_progress
        return Ok(new_progress)

    def get_progress(self, upload_id: str) -> UploadProgress | None:
        """Get upload progress."""
        return self._uploads.get(upload_id)

    async def generate_download_url(
        self,
        key: str,
        expiration: timedelta = timedelta(hours=1),
    ) -> Result[str, Exception]:
        """Generate signed download URL.

        **Validates: Requirements 17.5**
        """
        return await self._storage.generate_signed_url(key, expiration, "GET")
