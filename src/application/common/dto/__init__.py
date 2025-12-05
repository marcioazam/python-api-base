"""Generic DTOs for API communication.

Organized into subpackages by responsibility:
- responses/: API response wrappers (ApiResponse, PaginatedResponse, ProblemDetail)
- requests/: API request models (BulkDeleteRequest, BulkDeleteResponse)

**Feature: application-layer-improvements-2025**
"""

from application.common.dto.requests import (
    BulkDeleteRequest,
    BulkDeleteResponse,
)
from application.common.dto.responses import (
    ApiResponse,
    PaginatedResponse,
    ProblemDetail,
)

__all__ = [
    "ApiResponse",
    "BulkDeleteRequest",
    "BulkDeleteResponse",
    "PaginatedResponse",
    "ProblemDetail",
]
