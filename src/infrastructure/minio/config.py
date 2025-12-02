"""MinIO configuration.

**Feature: enterprise-infrastructure-2025**
**Requirement: R3 - MinIO Object Storage**
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta


@dataclass
class MinIOConfig:
    """Configuration for MinIO client.

    **Requirement: R3.1 - Configurable endpoint, credentials, and bucket**

    Attributes:
        endpoint: MinIO server endpoint
        access_key: Access key ID
        secret_key: Secret access key
        bucket: Default bucket name
        secure: Use HTTPS
        region: S3 region
        presigned_expiry: Default presigned URL expiry
        max_presigned_expiry: Maximum allowed presigned URL expiry
        multipart_threshold: Size threshold for multipart upload
        multipart_chunk_size: Chunk size for multipart upload
        allowed_content_types: Allowed content types for upload
        max_file_size: Maximum file size in bytes
    """

    endpoint: str = "localhost:9000"
    access_key: str = "minioadmin"
    secret_key: str = "minioadmin"
    bucket: str = "uploads"
    secure: bool = False
    region: str | None = None

    # Presigned URLs
    presigned_expiry: timedelta = timedelta(hours=1)
    max_presigned_expiry: timedelta = timedelta(hours=24)

    # Multipart upload
    multipart_threshold: int = 5 * 1024 * 1024  # 5MB
    multipart_chunk_size: int = 5 * 1024 * 1024  # 5MB

    # Security
    allowed_content_types: list[str] | None = None
    max_file_size: int = 100 * 1024 * 1024  # 100MB
