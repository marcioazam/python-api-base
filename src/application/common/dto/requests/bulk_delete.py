"""Bulk delete request/response DTOs.

Provides request and response models for bulk delete operations.

**Feature: architecture-validation-fixes-2025**
"""

from pydantic import BaseModel, Field


class BulkDeleteRequest(BaseModel):
    """Request model for bulk delete operations.

    Specifies a list of IDs to delete in a single operation.

    Example:
        >>> request = BulkDeleteRequest(ids=["id1", "id2", "id3"])
    """

    ids: list[str] = Field(..., min_length=1, description="List of IDs to delete")


class BulkDeleteResponse(BaseModel):
    """Response model for bulk delete operations.

    Returns the count of successfully deleted items and list of failed IDs.

    Example:
        >>> response = BulkDeleteResponse(
        ...     deleted_count=2,
        ...     failed_ids=["id3"]
        ... )
    """

    deleted_count: int = Field(ge=0, description="Number of successfully deleted items")
    failed_ids: list[str] = Field(
        default_factory=list, description="List of IDs that failed to delete"
    )
