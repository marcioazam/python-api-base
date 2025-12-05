"""Redis cache endpoints.

Demonstrates Redis cache usage with TTL and pattern operations.

**Feature: enterprise-infrastructure-2025**
**Refactored: Split from infrastructure_router.py for SRP compliance**
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from core.config import (
    STORAGE_TTL_DEFAULT_SECONDS,
    STORAGE_TTL_MAX_SECONDS,
    STORAGE_TTL_MIN_SECONDS,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cache", tags=["Cache"])


# =============================================================================
# DTOs
# =============================================================================


class CacheSetRequest(BaseModel):
    """Request to set cache value."""

    key: str = Field(..., min_length=1, max_length=256, examples=["user:123"])
    value: dict[str, Any] = Field(
        ..., examples=[{"name": "John", "email": "john@example.com"}]
    )
    ttl: int | None = Field(
        default=STORAGE_TTL_DEFAULT_SECONDS,
        ge=STORAGE_TTL_MIN_SECONDS,
        le=STORAGE_TTL_MAX_SECONDS,
        description="TTL in seconds",
    )


class CacheResponse(BaseModel):
    """Cache operation response."""

    key: str
    value: dict[str, Any] | None = None
    found: bool = False
    message: str | None = None


# =============================================================================
# Dependencies
# =============================================================================


def get_redis(request: Request) -> Any:
    """Get Redis client from app state.

    Returns:
        Redis client instance.

    Raises:
        HTTPException: 503 if Redis not configured.
    """
    redis = getattr(request.app.state, "redis", None)
    if redis is None:
        raise HTTPException(
            status_code=503,
            detail="Redis not configured. Set OBSERVABILITY__REDIS_ENABLED=true",
        )
    return redis


# =============================================================================
# Endpoints
# =============================================================================


@router.post(
    "",
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
    "/{key}",
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
    "/{key}",
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
    "/pattern/{pattern}",
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
    "/status",
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
