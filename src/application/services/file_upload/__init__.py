"""File upload service with S3 support and PEP 695 generics.

**Feature: enterprise-features-2025, Task 6.1: Create file upload service package**
**Validates: Requirements 6.8, 6.9**
"""

from .models import (
    FileMetadata,
    FileValidationConfig,
    StorageProvider,
    UploadError,
    UploadResult,
)
from .service import FileUploadService
from .validators import validate_file

__all__ = [
    "FileMetadata",
    "FileUploadService",
    "FileValidationConfig",
    "StorageProvider",
    "UploadError",
    "UploadResult",
    "validate_file",
]
