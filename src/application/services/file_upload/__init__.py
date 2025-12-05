"""File upload service with S3 support and PEP 695 generics.

Organized into subpackages by responsibility:
- models/: Data models and DTOs
- validators/: Validation logic
- service/: Main upload service

**Feature: enterprise-features-2025, Task 6.1: Create file upload service package**
**Validates: Requirements 6.8, 6.9**
"""

from application.services.file_upload.models import (
    FileMetadata,
    FileValidationConfig,
    StorageProvider,
    UploadError,
    UploadResult,
)
from application.services.file_upload.service import FileUploadService
from application.services.file_upload.validators import validate_file

__all__ = [
    "FileMetadata",
    "FileUploadService",
    "FileValidationConfig",
    "StorageProvider",
    "UploadError",
    "UploadResult",
    "validate_file",
]
