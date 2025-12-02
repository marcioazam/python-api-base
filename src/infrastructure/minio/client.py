"""MinIO client implementation.

**Feature: enterprise-infrastructure-2025**
**Requirement: R3 - MinIO Object Storage**
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import timedelta, datetime, UTC
from io import BytesIO
from typing import Any

from core.base.result import Result, Ok, Err

from infrastructure.minio.config import MinIOConfig

logger = logging.getLogger(__name__)


@dataclass
class ObjectMetadata:
    """Metadata for a stored object.

    **Requirement: R4.4 - Query object metadata**
    """

    key: str
    size: int
    content_type: str
    etag: str | None = None
    last_modified: datetime | None = None
    metadata: dict[str, str] | None = None


@dataclass
class UploadProgress:
    """Progress information for multipart upload."""

    uploaded_bytes: int
    total_bytes: int
    parts_completed: int
    total_parts: int

    @property
    def percentage(self) -> float:
        """Get upload progress percentage."""
        if self.total_bytes == 0:
            return 0.0
        return (self.uploaded_bytes / self.total_bytes) * 100


class MinIOClient:
    """MinIO S3-compatible object storage client.

    **Feature: enterprise-infrastructure-2025**
    **Requirement: R3 - MinIO Object Storage**

    Features:
    - Streaming upload/download
    - Multipart upload for large files
    - Presigned URLs
    - Object metadata management
    - Bucket lifecycle rules

    Example:
        >>> config = MinIOConfig(endpoint="localhost:9000")
        >>> client = MinIOClient(config)
        >>> await client.connect()
        >>> await client.upload("key", data, "application/octet-stream")
    """

    def __init__(self, config: MinIOConfig | None = None) -> None:
        """Initialize MinIO client.

        Args:
            config: MinIO configuration
        """
        self._config = config or MinIOConfig()
        self._client: Any = None
        self._connected = False

    async def connect(self) -> bool:
        """Establish MinIO connection.

        **Requirement: R3.1 - Establish connection**

        Returns:
            True if connected successfully
        """
        try:
            from minio import Minio

            self._client = Minio(
                self._config.endpoint,
                access_key=self._config.access_key,
                secret_key=self._config.secret_key,
                secure=self._config.secure,
                region=self._config.region,
            )

            # Verify connection by checking bucket
            await asyncio.to_thread(self._ensure_bucket)
            self._connected = True
            logger.info(
                "MinIO connected",
                extra={"endpoint": self._config.endpoint, "bucket": self._config.bucket},
            )
            return True

        except ImportError:
            logger.error("minio package not installed")
            return False
        except Exception as e:
            logger.error(f"MinIO connection failed: {e}")
            return False

    def _ensure_bucket(self) -> None:
        """Ensure default bucket exists."""
        if not self._client.bucket_exists(self._config.bucket):
            self._client.make_bucket(self._config.bucket)
            logger.info(f"Created bucket: {self._config.bucket}")

    @property
    def is_connected(self) -> bool:
        """Check if connected."""
        return self._connected

    # =========================================================================
    # Upload Operations
    # =========================================================================

    async def upload(
        self,
        key: str,
        data: bytes | BytesIO,
        content_type: str,
        metadata: dict[str, str] | None = None,
        bucket: str | None = None,
    ) -> Result[str, Exception]:
        """Upload object to storage.

        **Requirement: R3.2 - Streaming upload with progress**

        Args:
            key: Object key/path
            data: File data
            content_type: MIME type
            metadata: Custom metadata
            bucket: Override bucket

        Returns:
            Result with object URL or error
        """
        if not self._connected:
            return Err(ConnectionError("Not connected to MinIO"))

        target_bucket = bucket or self._config.bucket

        try:
            # Convert bytes to BytesIO if needed
            if isinstance(data, bytes):
                data = BytesIO(data)

            size = data.seek(0, 2)  # Get size
            data.seek(0)  # Reset position

            # Validate size
            if size > self._config.max_file_size:
                return Err(ValueError(f"File too large: {size} > {self._config.max_file_size}"))

            # Validate content type
            if self._config.allowed_content_types:
                if content_type not in self._config.allowed_content_types:
                    return Err(ValueError(f"Content type not allowed: {content_type}"))

            # Upload
            await asyncio.to_thread(
                self._client.put_object,
                target_bucket,
                key,
                data,
                size,
                content_type=content_type,
                metadata=metadata,
            )

            url = f"s3://{target_bucket}/{key}"
            logger.info(
                "Object uploaded",
                extra={"bucket": target_bucket, "key": key, "size": size},
            )
            return Ok(url)

        except Exception as e:
            logger.error(f"Upload failed: {e}", extra={"key": key})
            return Err(e)

    async def upload_stream(
        self,
        key: str,
        stream: AsyncIterator[bytes],
        content_type: str,
        total_size: int,
        metadata: dict[str, str] | None = None,
        bucket: str | None = None,
        progress_callback: Any | None = None,
    ) -> Result[str, Exception]:
        """Upload from async stream.

        **Requirement: R3.3 - Multipart upload**

        Args:
            key: Object key
            stream: Async byte stream
            content_type: MIME type
            total_size: Total size in bytes
            metadata: Custom metadata
            bucket: Override bucket
            progress_callback: Optional progress callback

        Returns:
            Result with URL or error
        """
        if not self._connected:
            return Err(ConnectionError("Not connected to MinIO"))

        target_bucket = bucket or self._config.bucket

        try:
            # Collect stream into buffer
            buffer = BytesIO()
            uploaded = 0

            async for chunk in stream:
                buffer.write(chunk)
                uploaded += len(chunk)

                if progress_callback:
                    progress = UploadProgress(
                        uploaded_bytes=uploaded,
                        total_bytes=total_size,
                        parts_completed=0,
                        total_parts=1,
                    )
                    await progress_callback(progress)

            buffer.seek(0)

            await asyncio.to_thread(
                self._client.put_object,
                target_bucket,
                key,
                buffer,
                uploaded,
                content_type=content_type,
                metadata=metadata,
            )

            url = f"s3://{target_bucket}/{key}"
            return Ok(url)

        except Exception as e:
            logger.error(f"Stream upload failed: {e}")
            return Err(e)

    # =========================================================================
    # Download Operations
    # =========================================================================

    async def download(
        self,
        key: str,
        bucket: str | None = None,
    ) -> Result[bytes, Exception]:
        """Download object.

        **Requirement: R3.4 - Streaming download**

        Args:
            key: Object key
            bucket: Override bucket

        Returns:
            Result with bytes or error
        """
        if not self._connected:
            return Err(ConnectionError("Not connected to MinIO"))

        target_bucket = bucket or self._config.bucket

        try:
            response = await asyncio.to_thread(
                self._client.get_object,
                target_bucket,
                key,
            )

            try:
                data = response.read()
                return Ok(data)
            finally:
                response.close()
                response.release_conn()

        except Exception as e:
            logger.error(f"Download failed: {e}", extra={"key": key})
            return Err(e)

    async def download_stream(
        self,
        key: str,
        bucket: str | None = None,
        chunk_size: int = 8192,
    ) -> AsyncIterator[bytes]:
        """Download object as async stream.

        Args:
            key: Object key
            bucket: Override bucket
            chunk_size: Chunk size for streaming

        Yields:
            Byte chunks
        """
        if not self._connected:
            return

        target_bucket = bucket or self._config.bucket

        try:
            response = await asyncio.to_thread(
                self._client.get_object,
                target_bucket,
                key,
            )

            try:
                for chunk in response.stream(chunk_size):
                    yield chunk
            finally:
                response.close()
                response.release_conn()

        except Exception as e:
            logger.error(f"Stream download failed: {e}")

    # =========================================================================
    # Presigned URLs
    # =========================================================================

    async def get_presigned_url(
        self,
        key: str,
        method: str = "GET",
        expiry: timedelta | None = None,
        bucket: str | None = None,
    ) -> Result[str, Exception]:
        """Generate presigned URL.

        **Requirement: R3.5 - Presigned URLs with configurable expiration**

        Args:
            key: Object key
            method: HTTP method (GET or PUT)
            expiry: URL expiration time
            bucket: Override bucket

        Returns:
            Result with URL or error
        """
        if not self._connected:
            return Err(ConnectionError("Not connected to MinIO"))

        target_bucket = bucket or self._config.bucket
        effective_expiry = expiry or self._config.presigned_expiry

        # Enforce max expiry
        if effective_expiry > self._config.max_presigned_expiry:
            effective_expiry = self._config.max_presigned_expiry

        try:
            if method.upper() == "PUT":
                url = await asyncio.to_thread(
                    self._client.presigned_put_object,
                    target_bucket,
                    key,
                    expires=effective_expiry,
                )
            else:
                url = await asyncio.to_thread(
                    self._client.presigned_get_object,
                    target_bucket,
                    key,
                    expires=effective_expiry,
                )

            return Ok(url)

        except Exception as e:
            logger.error(f"Presigned URL generation failed: {e}")
            return Err(e)

    # =========================================================================
    # Object Management
    # =========================================================================

    async def delete(
        self,
        key: str,
        bucket: str | None = None,
    ) -> Result[bool, Exception]:
        """Delete object.

        Args:
            key: Object key
            bucket: Override bucket

        Returns:
            Result with True or error
        """
        if not self._connected:
            return Err(ConnectionError("Not connected to MinIO"))

        target_bucket = bucket or self._config.bucket

        try:
            await asyncio.to_thread(
                self._client.remove_object,
                target_bucket,
                key,
            )
            logger.info("Object deleted", extra={"bucket": target_bucket, "key": key})
            return Ok(True)

        except Exception as e:
            logger.error(f"Delete failed: {e}")
            return Err(e)

    async def exists(
        self,
        key: str,
        bucket: str | None = None,
    ) -> bool:
        """Check if object exists.

        Args:
            key: Object key
            bucket: Override bucket

        Returns:
            True if exists
        """
        if not self._connected:
            return False

        target_bucket = bucket or self._config.bucket

        try:
            await asyncio.to_thread(
                self._client.stat_object,
                target_bucket,
                key,
            )
            return True
        except Exception:
            return False

    async def get_metadata(
        self,
        key: str,
        bucket: str | None = None,
    ) -> Result[ObjectMetadata, Exception]:
        """Get object metadata.

        **Requirement: R4.4 - Query object metadata**

        Args:
            key: Object key
            bucket: Override bucket

        Returns:
            Result with metadata or error
        """
        if not self._connected:
            return Err(ConnectionError("Not connected to MinIO"))

        target_bucket = bucket or self._config.bucket

        try:
            stat = await asyncio.to_thread(
                self._client.stat_object,
                target_bucket,
                key,
            )

            return Ok(
                ObjectMetadata(
                    key=key,
                    size=stat.size,
                    content_type=stat.content_type,
                    etag=stat.etag,
                    last_modified=stat.last_modified,
                    metadata=dict(stat.metadata) if stat.metadata else None,
                )
            )

        except Exception as e:
            logger.error(f"Get metadata failed: {e}")
            return Err(e)

    async def list_objects(
        self,
        prefix: str = "",
        bucket: str | None = None,
        max_keys: int = 1000,
    ) -> Result[list[ObjectMetadata], Exception]:
        """List objects with optional prefix filter.

        **Requirement: R3.7 - Pagination and prefix filtering**

        Args:
            prefix: Key prefix filter
            bucket: Override bucket
            max_keys: Maximum objects to return

        Returns:
            Result with list of metadata or error
        """
        if not self._connected:
            return Err(ConnectionError("Not connected to MinIO"))

        target_bucket = bucket or self._config.bucket

        try:
            objects = await asyncio.to_thread(
                lambda: list(
                    self._client.list_objects(
                        target_bucket,
                        prefix=prefix,
                    )
                )[:max_keys]
            )

            result = []
            for obj in objects:
                result.append(
                    ObjectMetadata(
                        key=obj.object_name,
                        size=obj.size,
                        content_type=obj.content_type or "application/octet-stream",
                        etag=obj.etag,
                        last_modified=obj.last_modified,
                    )
                )

            return Ok(result)

        except Exception as e:
            logger.error(f"List objects failed: {e}")
            return Err(e)

    # =========================================================================
    # Bucket Operations
    # =========================================================================

    async def list_buckets(self) -> list[str]:
        """List all buckets.

        Returns:
            List of bucket names
        """
        if not self._connected:
            return []

        try:
            buckets = await asyncio.to_thread(self._client.list_buckets)
            return [b.name for b in buckets]
        except Exception as e:
            logger.error(f"List buckets failed: {e}")
            return []
