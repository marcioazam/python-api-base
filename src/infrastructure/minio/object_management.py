"""MinIO object management operations.

**Feature: enterprise-infrastructure-2025**
**Refactored: 2025 - Extracted from client.py for SRP compliance**
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from core.base.result import Err, Ok, Result

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


class ObjectManagement:
    """MinIO object management operations handler."""

    def __init__(
        self,
        client: Any,
        default_bucket: str,
        presigned_expiry: timedelta,
        max_presigned_expiry: timedelta,
    ) -> None:
        """Initialize object management."""
        self._client = client
        self._default_bucket = default_bucket
        self._presigned_expiry = presigned_expiry
        self._max_presigned_expiry = max_presigned_expiry

    async def get_presigned_url(
        self,
        key: str,
        method: str = "GET",
        expiry: timedelta | None = None,
        bucket: str | None = None,
    ) -> Result[str, Exception]:
        """Generate presigned URL.

        **Requirement: R3.5 - Presigned URLs with configurable expiration**
        """
        target_bucket = bucket or self._default_bucket
        effective_expiry = expiry or self._presigned_expiry

        effective_expiry = min(effective_expiry, self._max_presigned_expiry)

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

    async def delete(
        self,
        key: str,
        bucket: str | None = None,
    ) -> Result[bool, Exception]:
        """Delete object."""
        target_bucket = bucket or self._default_bucket

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
        """Check if object exists."""
        target_bucket = bucket or self._default_bucket

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
        """
        target_bucket = bucket or self._default_bucket

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
        """
        target_bucket = bucket or self._default_bucket

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

    async def list_buckets(self) -> list[str]:
        """List all buckets."""
        try:
            buckets = await asyncio.to_thread(self._client.list_buckets)
            return [b.name for b in buckets]
        except Exception as e:
            logger.error(f"List buckets failed: {e}")
            return []
