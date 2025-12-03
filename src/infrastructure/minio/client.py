"""MinIO client implementation.

**Feature: enterprise-infrastructure-2025**
**Requirement: R3 - MinIO Object Storage**
**Refactored: 2025 - Split 471 lines into focused modules**
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from datetime import timedelta
from io import BytesIO
from typing import Any

from core.base.patterns.result import Result, Err

from infrastructure.minio.config import MinIOConfig
from infrastructure.minio.download_operations import DownloadOperations
from infrastructure.minio.object_management import ObjectManagement, ObjectMetadata
from infrastructure.minio.upload_operations import UploadOperations, UploadProgress

logger = logging.getLogger(__name__)


class MinIOClient:
    """MinIO S3-compatible object storage client.

    **Feature: enterprise-infrastructure-2025**
    **Requirement: R3 - MinIO Object Storage**
    **Refactored: 2025 - Delegated operations to focused classes**

    Features:
    - Streaming upload/download
    - Multipart upload for large files
    - Presigned URLs
    - Object metadata management
    - Bucket lifecycle rules
    """

    def __init__(self, config: MinIOConfig | None = None) -> None:
        """Initialize MinIO client."""
        self._config = config or MinIOConfig()
        self._client: Any = None
        self._connected = False
        self._upload_ops: UploadOperations | None = None
        self._download_ops: DownloadOperations | None = None
        self._object_mgmt: ObjectManagement | None = None

    async def connect(self) -> bool:
        """Establish MinIO connection.

        **Requirement: R3.1 - Establish connection**
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

            await asyncio.to_thread(self._ensure_bucket)
            self._connected = True
            self._init_operations()

            logger.info(
                "MinIO connected",
                extra={
                    "endpoint": self._config.endpoint,
                    "bucket": self._config.bucket,
                },
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

    def _init_operations(self) -> None:
        """Initialize operation handlers."""
        self._upload_ops = UploadOperations(
            client=self._client,
            default_bucket=self._config.bucket,
            max_file_size=self._config.max_file_size,
            allowed_content_types=self._config.allowed_content_types,
        )
        self._download_ops = DownloadOperations(
            client=self._client,
            default_bucket=self._config.bucket,
        )
        self._object_mgmt = ObjectManagement(
            client=self._client,
            default_bucket=self._config.bucket,
            presigned_expiry=self._config.presigned_expiry,
            max_presigned_expiry=self._config.max_presigned_expiry,
        )

    @property
    def is_connected(self) -> bool:
        """Check if connected."""
        return self._connected

    # Upload Operations (delegated)

    async def upload(
        self,
        key: str,
        data: bytes | BytesIO,
        content_type: str,
        metadata: dict[str, str] | None = None,
        bucket: str | None = None,
    ) -> Result[str, Exception]:
        """Upload object to storage."""
        if not self._connected or not self._upload_ops:
            return Err(ConnectionError("Not connected to MinIO"))
        return await self._upload_ops.upload(key, data, content_type, metadata, bucket)

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
        """Upload from async stream."""
        if not self._connected or not self._upload_ops:
            return Err(ConnectionError("Not connected to MinIO"))
        return await self._upload_ops.upload_stream(
            key, stream, content_type, total_size, metadata, bucket, progress_callback
        )

    # Download Operations (delegated)

    async def download(
        self,
        key: str,
        bucket: str | None = None,
    ) -> Result[bytes, Exception]:
        """Download object."""
        if not self._connected or not self._download_ops:
            return Err(ConnectionError("Not connected to MinIO"))
        return await self._download_ops.download(key, bucket)

    async def download_stream(
        self,
        key: str,
        bucket: str | None = None,
        chunk_size: int = 8192,
    ) -> AsyncIterator[bytes]:
        """Download object as async stream."""
        if not self._connected or not self._download_ops:
            return
        async for chunk in self._download_ops.download_stream(key, bucket, chunk_size):
            yield chunk

    # Object Management (delegated)

    async def get_presigned_url(
        self,
        key: str,
        method: str = "GET",
        expiry: timedelta | None = None,
        bucket: str | None = None,
    ) -> Result[str, Exception]:
        """Generate presigned URL."""
        if not self._connected or not self._object_mgmt:
            return Err(ConnectionError("Not connected to MinIO"))
        return await self._object_mgmt.get_presigned_url(key, method, expiry, bucket)

    async def delete(
        self,
        key: str,
        bucket: str | None = None,
    ) -> Result[bool, Exception]:
        """Delete object."""
        if not self._connected or not self._object_mgmt:
            return Err(ConnectionError("Not connected to MinIO"))
        return await self._object_mgmt.delete(key, bucket)

    async def exists(
        self,
        key: str,
        bucket: str | None = None,
    ) -> bool:
        """Check if object exists."""
        if not self._connected or not self._object_mgmt:
            return False
        return await self._object_mgmt.exists(key, bucket)

    async def get_metadata(
        self,
        key: str,
        bucket: str | None = None,
    ) -> Result[ObjectMetadata, Exception]:
        """Get object metadata."""
        if not self._connected or not self._object_mgmt:
            return Err(ConnectionError("Not connected to MinIO"))
        return await self._object_mgmt.get_metadata(key, bucket)

    async def list_objects(
        self,
        prefix: str = "",
        bucket: str | None = None,
        max_keys: int = 1000,
    ) -> Result[list[ObjectMetadata], Exception]:
        """List objects with optional prefix filter."""
        if not self._connected or not self._object_mgmt:
            return Err(ConnectionError("Not connected to MinIO"))
        return await self._object_mgmt.list_objects(prefix, bucket, max_keys)

    async def list_buckets(self) -> list[str]:
        """List all buckets."""
        if not self._connected or not self._object_mgmt:
            return []
        return await self._object_mgmt.list_buckets()


# Re-exports for backward compatibility
__all__ = [
    "MinIOClient",
    "ObjectMetadata",
    "UploadProgress",
]
