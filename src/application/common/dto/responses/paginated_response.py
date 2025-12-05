"""Paginated response DTO with computed navigation fields.

Provides standard paginated response wrapper with automatic pagination metadata.

**Feature: application-layer-improvements-2025**
"""

from pydantic import BaseModel, Field, computed_field


class PaginatedResponse[T](BaseModel):
    """Generic paginated response.

    Contains a list of items along with pagination metadata
    including computed fields for total pages and navigation flags.

    Type Parameters:
        T: The type of items in the paginated list.

    Example:
        >>> response = PaginatedResponse(
        ...     items=[{"id": "1"}, {"id": "2"}],
        ...     total=100,
        ...     page=1,
        ...     size=2
        ... )
        >>> response.pages  # 50
        >>> response.has_next  # True
    """

    items: list[T] = Field(description="List of items for current page")
    total: int = Field(ge=0, description="Total number of items across all pages")
    page: int = Field(ge=1, description="Current page number (1-indexed)")
    size: int = Field(ge=1, le=100, description="Number of items per page")

    @computed_field
    @property
    def pages(self) -> int:
        """Calculate total number of pages.

        Returns:
            Total number of pages needed to display all items.
        """
        if self.total == 0:
            return 0
        return (self.total + self.size - 1) // self.size

    @computed_field
    @property
    def has_next(self) -> bool:
        """Check if there is a next page.

        Returns:
            True if current page is not the last page.
        """
        return self.page < self.pages

    @computed_field
    @property
    def has_previous(self) -> bool:
        """Check if there is a previous page.

        Returns:
            True if current page is not the first page.
        """
        return self.page > 1

    model_config = {"from_attributes": True}
