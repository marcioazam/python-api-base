"""MinIO S3-compatible object storage.

**Feature: enterprise-infrastructure-2025**
**Requirement: R3 - MinIO Object Storage**
**Refactored: 2025 - Split into focused modules**
"""

from infrastructure.minio.client import MinIOClient, ObjectMetadata, UploadProgress
from infrastructure.minio.config import MinIOConfig

__all__ = [
    "MinIOClient",
    "MinIOConfig",
    "ObjectMetadata",
    "UploadProgress",
]
