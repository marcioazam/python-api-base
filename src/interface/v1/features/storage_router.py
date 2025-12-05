"""MinIO storage endpoints.

Demonstrates MinIO storage usage with upload, download, and presigned URLs.

**Feature: enterprise-infrastructure-2025**
**Refactored: Split from infrastructure_router.py for SRP compliance**
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from pydantic import BaseModel

from core.config import MAX_STORAGE_LIST_KEYS, PRESIGNED_URL_EXPIRE_SECONDS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/storage", tags=["Storage"])


# =============================================================================
# DTOs
# =============================================================================


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


def get_minio(request: Request) -> Any:
    """Get MinIO client from app state.

    Returns:
        MinIO client instance.

    Raises:
        HTTPException: 503 if MinIO not configured.
    """
    minio = getattr(request.app.state, "minio", None)
    if minio is None:
        raise HTTPException(
            status_code=503,
            detail="MinIO not configured. Set OBSERVABILITY__MINIO_ENABLED=true",
        )
    return minio


# =============================================================================
# Endpoints
# =============================================================================


@router.post(
    "/upload",
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
    "/{key:path}",
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
    "/{key:path}/presigned",
    response_model=PresignedUrlResponse,
    summary="Get presigned URL",
    description="Generate a presigned URL for direct file access",
)
async def storage_presigned_url(
    key: str,
    expires_in: int = PRESIGNED_URL_EXPIRE_SECONDS,
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
    "/{key:path}",
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
    "",
    summary="List files",
    description="List files in MinIO storage with optional prefix filter",
)
async def storage_list(
    prefix: str = "",
    max_keys: int = MAX_STORAGE_LIST_KEYS,
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
                "last_modified": obj.last_modified.isoformat()
                if obj.last_modified
                else None,
            }
            for obj in objects
        ],
    }
