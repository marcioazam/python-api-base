"""MinIO storage provider implementation.

**Feature: infrastructure-modules-workflow-analysis**
**Validates: Requirements 1.2**

Implements FileStorage protocol using MinIO client.
"""

from datetime import timedelta
from typing import Any

from collections.abc import AsyncIterator

from core.base.patterns.result import Err, Ok, Result
from infrastructure.minio import MinIOClient


class MinIOStorageProvider:
    """MinIO implementation of FileStorage protocol.

    **Feature: infrastructure-modules-workflow-analysis**
    **Validates: Requirements 1.2**
    """

    def __init__(self, client: MinIOClient) -> None:
        """Initialize MinIO storage provider.

        Args:
            client: MinIO client instance.
        """
        self._client = client

    async def upload(
        self,
        key: str,
        data: bytes | AsyncIterator[bytes],
        content_type: str,
    ) -> Result[str, Exception]:
        """Upload file to MinIO.

        Args:
            key: Storage key/path.
            data: File data or async stream.
            content_type: MIME type.

        Returns:
            Ok with storage URL or Err with exception.
        """
        try:
            if isinstance(data, bytes):
                await self._client.upload_bytes(key, data, content_type)
            else:
                # Collect async iterator to bytes
                chunks = []
                async for chunk in data:
                    chunks.append(chunk)
                await self._client.upload_bytes(key, b"".join(chunks), content_type)
            
            url = f"{self._client._config.endpoint}/{self._client._config.bucket}/{key}"
            return Ok(url)
        except Exception as e:
            return Err(e)

    async def download(self, key: str) -> Result[bytes, Exception]:
        """Download file from MinIO.

        Args:
            key: Storage key/path.

        Returns:
            Ok with file bytes or Err with exception.
        """
        try:
            data = await self._client.download_bytes(key)
            return Ok(data)
        except Exception as e:
            return Err(e)

    async def delete(self, key: str) -> Result[bool, Exception]:
        """Delete file from MinIO.

        Args:
            key: Storage key/path.

        Returns:
            Ok with True if deleted, Err with exception.
        """
        try:
            await self._client.delete(key)
            return Ok(True)
        except Exception as e:
            return Err(e)

    async def exists(self, key: str) -> bool:
        """Check if file exists in MinIO."""
        try:
            return await self._client.exists(key)
        except Exception:
            return False

    async def generate_signed_url(
        self,
        key: str,
        expiration: timedelta,
        operation: str = "GET",
    ) -> Result[str, Exception]:
        """Generate signed URL for file access.

        Args:
            key: Storage key/path.
            expiration: URL expiration time.
            operation: HTTP operation (GET, PUT).

        Returns:
            Ok with signed URL or Err with exception.
        """
        try:
            url = await self._client.get_presigned_url(
                key,
                expires=int(expiration.total_seconds()),
                method=operation,
            )
            return Ok(url)
        except Exception as e:
            return Err(e)


__all__ = ["MinIOStorageProvider"]
