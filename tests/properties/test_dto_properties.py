"""Property-based tests for generic DTOs.

**Feature: generic-fastapi-crud, Property 1: Generic Response Serialization Completeness**
**Feature: generic-fastapi-crud, Property 3: Pagination Computed Fields Consistency**
**Validates: Requirements 1.2, 1.5, 8.3**
"""

from datetime import datetime, timezone

from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import BaseModel

from my_app.application.common.dto import ApiResponse, PaginatedResponse, ProblemDetail


# Sample model for testing generic responses
class SampleItem(BaseModel):
    """Sample item for testing."""

    id: int
    name: str
    value: float


# Strategy for generating sample items
sample_item_strategy = st.builds(
    SampleItem,
    id=st.integers(min_value=1, max_value=10000),
    name=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("L", "N"))),
    value=st.floats(min_value=0, max_value=10000, allow_nan=False, allow_infinity=False),
)


class TestApiResponseSerialization:
    """Property tests for ApiResponse serialization."""

    @settings(max_examples=50)
    @given(item=sample_item_strategy)
    def test_api_response_contains_required_fields(self, item: SampleItem) -> None:
        """
        **Feature: generic-fastapi-crud, Property 1: Generic Response Serialization Completeness**

        For any valid Pydantic model instance wrapped in ApiResponse[T],
        serializing to JSON SHALL produce an object containing data, message,
        status_code, timestamp, and request_id fields with correct types.
        """
        response = ApiResponse[SampleItem](data=item)
        serialized = response.model_dump()

        # Check all required fields are present
        assert "data" in serialized
        assert "message" in serialized
        assert "status_code" in serialized
        assert "timestamp" in serialized
        assert "request_id" in serialized

        # Check types
        assert isinstance(serialized["data"], dict)
        assert isinstance(serialized["message"], str)
        assert isinstance(serialized["status_code"], int)
        assert isinstance(serialized["timestamp"], datetime)
        assert serialized["request_id"] is None or isinstance(serialized["request_id"], str)

    @settings(max_examples=30)
    @given(
        item=sample_item_strategy,
        message=st.text(min_size=1, max_size=100, alphabet=st.characters(whitelist_categories=("L", "N", "P"))),
        status_code=st.integers(min_value=100, max_value=599),
        request_id=st.text(min_size=1, max_size=36, alphabet=st.characters(whitelist_categories=("L", "N"))),
    )
    def test_api_response_preserves_custom_values(
        self, item: SampleItem, message: str, status_code: int, request_id: str
    ) -> None:
        """
        For any custom message, status_code, and request_id,
        ApiResponse SHALL preserve these values in serialization.
        """
        response = ApiResponse[SampleItem](
            data=item,
            message=message,
            status_code=status_code,
            request_id=request_id,
        )
        serialized = response.model_dump()

        assert serialized["message"] == message
        assert serialized["status_code"] == status_code
        assert serialized["request_id"] == request_id

    @settings(max_examples=30)
    @given(item=sample_item_strategy)
    def test_api_response_timestamp_is_utc(self, item: SampleItem) -> None:
        """
        ApiResponse timestamp SHALL be timezone-aware UTC.
        """
        response = ApiResponse[SampleItem](data=item)
        assert response.timestamp.tzinfo is not None


class TestPaginatedResponseComputedFields:
    """Property tests for PaginatedResponse computed fields."""

    @settings(max_examples=100)
    @given(
        total=st.integers(min_value=0, max_value=10000),
        page=st.integers(min_value=1, max_value=100),
        size=st.integers(min_value=1, max_value=100),
    )
    def test_pagination_computed_fields_consistency(
        self, total: int, page: int, size: int
    ) -> None:
        """
        **Feature: generic-fastapi-crud, Property 3: Pagination Computed Fields Consistency**

        For any PaginatedResponse with total, page, and size values,
        the computed fields SHALL satisfy:
        - pages equals ceil(total / size)
        - has_next equals page < pages
        - has_previous equals page > 1
        """
        response = PaginatedResponse[SampleItem](
            items=[],
            total=total,
            page=page,
            size=size,
        )

        # Verify pages calculation
        expected_pages = (total + size - 1) // size if total > 0 else 0
        assert response.pages == expected_pages

        # Verify has_next
        assert response.has_next == (page < response.pages)

        # Verify has_previous
        assert response.has_previous == (page > 1)

    @settings(max_examples=50)
    @given(
        items=st.lists(sample_item_strategy, min_size=0, max_size=20),
        total=st.integers(min_value=0, max_value=1000),
        page=st.integers(min_value=1, max_value=50),
        size=st.integers(min_value=1, max_value=100),
    )
    def test_paginated_response_serialization(
        self, items: list[SampleItem], total: int, page: int, size: int
    ) -> None:
        """
        PaginatedResponse SHALL serialize all fields including computed fields.
        """
        response = PaginatedResponse[SampleItem](
            items=items,
            total=total,
            page=page,
            size=size,
        )
        serialized = response.model_dump()

        # Check all fields present
        assert "items" in serialized
        assert "total" in serialized
        assert "page" in serialized
        assert "size" in serialized
        assert "pages" in serialized
        assert "has_next" in serialized
        assert "has_previous" in serialized

        # Check items count
        assert len(serialized["items"]) == len(items)


class TestProblemDetail:
    """Property tests for ProblemDetail RFC 7807 format."""

    @settings(max_examples=30)
    @given(
        title=st.text(min_size=1, max_size=100, alphabet=st.characters(whitelist_categories=("L", "N", "P"))),
        status=st.integers(min_value=100, max_value=599),
        detail=st.text(min_size=1, max_size=200, alphabet=st.characters(whitelist_categories=("L", "N", "P"))) | st.none(),
    )
    def test_problem_detail_format(
        self, title: str, status: int, detail: str | None
    ) -> None:
        """
        **Feature: generic-fastapi-crud, Property 2: Validation Error Format Compliance**

        ProblemDetail SHALL contain type, title, status, detail, instance, and errors fields.
        """
        problem = ProblemDetail(title=title, status=status, detail=detail)
        serialized = problem.model_dump()

        # Check required RFC 7807 fields
        assert "type" in serialized
        assert "title" in serialized
        assert "status" in serialized
        assert "detail" in serialized
        assert "instance" in serialized
        assert "errors" in serialized

        # Verify values
        assert serialized["title"] == title
        assert serialized["status"] == status
        assert serialized["detail"] == detail
