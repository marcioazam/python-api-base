"""MinIO S3-compatible object storage.

**Feature: enterprise-infrastructure-2025**
**Requirement: R3 - MinIO Object Storage**
"""

from infrastructure.minio.config import MinIOConfig
from infrastructure.minio.client import MinIOClient

__all__ = [
    "MinIOConfig",
    "MinIOClient",
]
