"""Infrastructure examples router (facade).

Aggregates cache, storage, and Kafka routers for backward compatibility.

**Feature: enterprise-infrastructure-2025**
**Refactored: Split into cache_router, storage_router, kafka_router for SRP**
"""

from __future__ import annotations

from fastapi import APIRouter

from interface.v1.cache_router import router as cache_router
from interface.v1.kafka_router import router as kafka_router
from interface.v1.storage_router import router as storage_router

# Re-export DTOs for backward compatibility
from interface.v1.cache_router import (
    CacheResponse,
    CacheSetRequest,
    cache_delete,
    cache_delete_pattern,
    cache_get,
    cache_set,
    cache_status,
    get_redis,
)
from interface.v1.kafka_router import (
    KafkaPublishRequest,
    KafkaPublishResponse,
    KafkaStatusResponse,
    get_kafka,
    kafka_publish,
    kafka_status,
)
from interface.v1.storage_router import (
    PresignedUrlResponse,
    StorageUploadResponse,
    get_minio,
    storage_delete,
    storage_download,
    storage_list,
    storage_presigned_url,
    storage_upload,
)

__all__ = [
    "router",
    # Cache DTOs and functions
    "CacheSetRequest",
    "CacheResponse",
    "get_redis",
    "cache_set",
    "cache_get",
    "cache_delete",
    "cache_delete_pattern",
    "cache_status",
    # Storage DTOs and functions
    "StorageUploadResponse",
    "PresignedUrlResponse",
    "get_minio",
    "storage_upload",
    "storage_download",
    "storage_presigned_url",
    "storage_delete",
    "storage_list",
    # Kafka DTOs and functions
    "KafkaPublishRequest",
    "KafkaPublishResponse",
    "KafkaStatusResponse",
    "get_kafka",
    "kafka_publish",
    "kafka_status",
]

# Create combined router
router = APIRouter(prefix="/infrastructure", tags=["Infrastructure Examples"])

# Include sub-routers
router.include_router(cache_router)
router.include_router(storage_router)
router.include_router(kafka_router)
