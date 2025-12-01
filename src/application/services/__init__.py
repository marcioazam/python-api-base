"""Cross-cutting application services.

Provides shared services used across bounded contexts:
- Feature Flags: Controlled feature rollouts
- File Upload: S3-compatible file handling
- Multitenancy: Tenant isolation

**Architecture: Cross-Cutting Concerns**
"""

from .feature_flags import FeatureFlagService, FlagConfig, FlagStatus
from .file_upload import FileUploadService, FileMetadata, UploadResult
from .multitenancy import TenantMiddleware, TenantContext, get_current_tenant

__all__ = [
    # Feature Flags
    "FeatureFlagService",
    "FlagConfig",
    "FlagStatus",
    # File Upload
    "FileUploadService",
    "FileMetadata",
    "UploadResult",
    # Multitenancy
    "TenantMiddleware",
    "TenantContext",
    "get_current_tenant",
]
