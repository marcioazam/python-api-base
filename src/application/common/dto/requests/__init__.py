"""Request DTOs for API communication.

Provides request models for API operations including bulk delete requests.

**Feature: architecture-validation-fixes-2025**
"""

from application.common.dto.requests.bulk_delete import (
    BulkDeleteRequest,
    BulkDeleteResponse,
)

__all__ = [
    "BulkDeleteRequest",
    "BulkDeleteResponse",
]
