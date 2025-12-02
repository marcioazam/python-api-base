"""Infrastructure examples router.

Demonstrates Redis cache and MinIO storage usage.

**Feature: enterprise-infrastructure-2025**
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from pydantic import BaseModel, Field

from core.errors import ProblemDetail

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/infrastructure", tags=["Infrastructure Examples"])


# =============================================================================
# DTOs
# =============================================================================


class CacheSetRequest(BaseModel):
    """Request to set cache value."""

    key: str = Field(..., min_length=1, max_length=256, examples=["user:123"])
    value: dict[str, Any] = Field(..., examples=[{"name": "John", "email": "john@example.com"}])
    ttl: int | None = Field(default=3600, ge=1, le=86400, description="TTL in seconds")


class CacheResponse(BaseModel):
    """Cache operation response."""

    key: str
    value: dict[str, Any] | None = None
    found: bool = False
    message: str | None = None


class StorageUploadResponse(BaseModel):
    """Storage upload response."""

    key: str
    url: str
    size: int
    content_type: str


class PresignedUrlResponse(BaseModel):
    """Presigned URL response."""

    key: str
    url: str
    expires_in_seconds: int


# =============================================================================
# Dependencies
# =============================================================================


def get_redis(request: Request):
    """Get Redis client from app state."""
    redis = getattr(request.app.state, "redis", None)
    if redis is None:
        raise HTTPException(
            status_code=503,
            detail="Redis not configured. Set OBSERVABILITY__REDIS_ENABLED=true",
        )
    return redis


def get_minio(request: Request):
    """Get MinIO client from app state."""
    minio = getattr(request.app.state, "minio", None)
    if minio is None:
        raise HTTPException(
            status_code=503,
            detail="MinIO not configured. Set OBSERVABILITY__MINIO_ENABLED=true",
        )
    return minio


# =============================================================================
# Redis Cache Endpoints
# =============================================================================


@router.post(
    "/cache",
    response_model=CacheResponse,
    summary="Set cache value",
    description="Store a value in Redis cache with optional TTL",
)
async def cache_set(
    request: CacheSetRequest,
    redis=Depends(get_redis),
) -> CacheResponse:
    """Set a value in Redis cache.

    **Requirement: R1.2 - Set operation with TTL**
    """
    success = await redis.set(request.key, request.value, request.ttl)

    return CacheResponse(
        key=request.key,
        value=request.value if success else None,
        found=success,
        message="Value cached successfully" if success else "Failed to cache value",
    )


@router.get(
    "/cache/{key}",
    response_model=CacheResponse,
    summary="Get cache value",
    description="Retrieve a value from Redis cache",
)
async def cache_get(
    key: str,
    redis=Depends(get_redis),
) -> CacheResponse:
    """Get a value from Redis cache.

    **Requirement: R1.2 - Get operation**
    """
    value = await redis.get(key)

    return CacheResponse(
        key=key,
        value=value,
        found=value is not None,
        message="Value found" if value else "Key not found",
    )


@router.delete(
    "/cache/{key}",
    response_model=CacheResponse,
    summary="Delete cache value",
    description="Remove a value from Redis cache",
)
async def cache_delete(
    key: str,
    redis=Depends(get_redis),
) -> CacheResponse:
    """Delete a value from Redis cache.

    **Requirement: R1.2 - Delete operation**
    """
    deleted = await redis.delete(key)

    return CacheResponse(
        key=key,
        found=deleted,
        message="Value deleted" if deleted else "Key not found",
    )


@router.delete(
    "/cache/pattern/{pattern}",
    summary="Delete by pattern",
    description="Delete all keys matching a pattern (e.g., user:*)",
)
async def cache_delete_pattern(
    pattern: str,
    redis=Depends(get_redis),
) -> dict[str, Any]:
    """Delete cache keys by pattern.

    **Requirement: R1.7 - Bulk invalidation using pattern**
    """
    deleted_count = await redis.delete_pattern(pattern)

    return {
        "pattern": pattern,
        "deleted_count": deleted_count,
        "message": f"Deleted {deleted_count} keys matching pattern",
    }


@router.get(
    "/cache/status",
    summary="Cache status",
    description="Get Redis cache status and circuit breaker state",
)
async def cache_status(
    redis=Depends(get_redis),
) -> dict[str, Any]:
    """Get Redis cache status.

    **Requirement: R1.5 - Circuit breaker state**
    """
    return {
        "connected": redis.is_connected,
        "circuit_state": redis.circuit_state,
        "using_fallback": redis.is_using_fallback,
    }


# =============================================================================
# MinIO Storage Endpoints
# =============================================================================


@router.post(
    "/storage/upload",
    response_model=StorageUploadResponse,
    summary="Upload file",
    description="Upload a file to MinIO storage",
)
async def storage_upload(
    file: UploadFile = File(...),
    minio=Depends(get_minio),
) -> StorageUploadResponse:
    """Upload a file to MinIO.

    **Requirement: R3.2 - Streaming upload**
    """
    content = await file.read()
    key = f"uploads/{file.filename}"

    result = await minio.upload(
        key=key,
        data=content,
        content_type=file.content_type or "application/octet-stream",
    )

    if result.is_err():
        raise HTTPException(status_code=500, detail=str(result.unwrap_err()))

    return StorageUploadResponse(
        key=key,
        url=result.unwrap(),
        size=len(content),
        content_type=file.content_type or "application/octet-stream",
    )


@router.get(
    "/storage/{key:path}",
    summary="Download file",
    description="Download a file from MinIO storage",
)
async def storage_download(
    key: str,
    minio=Depends(get_minio),
) -> bytes:
    """Download a file from MinIO.

    **Requirement: R3.4 - Download**
    """
    result = await minio.download(key)

    if result.is_err():
        raise HTTPException(status_code=404, detail="File not found")

    return result.unwrap()


@router.get(
    "/storage/{key:path}/presigned",
    response_model=PresignedUrlResponse,
    summary="Get presigned URL",
    description="Generate a presigned URL for direct file access",
)
async def storage_presigned_url(
    key: str,
    expires_in: int = 3600,
    minio=Depends(get_minio),
) -> PresignedUrlResponse:
    """Generate presigned URL for file.

    **Requirement: R3.5 - Presigned URLs with expiration**
    """
    result = await minio.get_presigned_url(
        key=key,
        expiry=timedelta(seconds=expires_in),
    )

    if result.is_err():
        raise HTTPException(status_code=404, detail="File not found")

    return PresignedUrlResponse(
        key=key,
        url=result.unwrap(),
        expires_in_seconds=expires_in,
    )


@router.delete(
    "/storage/{key:path}",
    summary="Delete file",
    description="Delete a file from MinIO storage",
)
async def storage_delete(
    key: str,
    minio=Depends(get_minio),
) -> dict[str, Any]:
    """Delete a file from MinIO.

    **Requirement: R3 - Delete**
    """
    result = await minio.delete(key)

    if result.is_err():
        raise HTTPException(status_code=500, detail=str(result.unwrap_err()))

    return {
        "key": key,
        "deleted": result.unwrap(),
        "message": "File deleted successfully",
    }


@router.get(
    "/storage",
    summary="List files",
    description="List files in MinIO storage with optional prefix filter",
)
async def storage_list(
    prefix: str = "",
    max_keys: int = 100,
    minio=Depends(get_minio),
) -> dict[str, Any]:
    """List files in storage.

    **Requirement: R3.7 - Pagination and prefix filtering**
    """
    result = await minio.list_objects(prefix=prefix, max_keys=max_keys)

    if result.is_err():
        raise HTTPException(status_code=500, detail=str(result.unwrap_err()))

    objects = result.unwrap()

    return {
        "prefix": prefix,
        "count": len(objects),
        "objects": [
            {
                "key": obj.key,
                "size": obj.size,
                "content_type": obj.content_type,
                "last_modified": obj.last_modified.isoformat() if obj.last_modified else None,
            }
            for obj in objects
        ],
    }
