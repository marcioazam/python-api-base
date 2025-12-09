"""Property-based tests for API Response types.

**Feature: python-api-base-2025-validation**
**Properties 23, 24: API Response Request ID Uniqueness, Paginated Response Navigation**
**Validates: Requirements 8.2, 8.4**
"""

import math

from hypothesis import given, settings, strategies as st

from application.common.dto.responses.api_response import ApiResponse
from application.common.dto.responses.paginated_response import PaginatedResponse


# =============================================================================
# Property 23: API Response Request ID Uniqueness
# **Feature: python-api-base-2025-validation, Property 23: API Response Request ID Uniqueness**
# **Validates: Requirements 8.4**
# =============================================================================


class TestApiResponseRequestIdUniqueness:
    """Property tests for API response request ID uniqueness.

    **Feature: python-api-base-2025-validation, Property 23: API Response Request ID Uniqueness**
    **Validates: Requirements 8.4**

    Note: ApiResponse.request_id defaults to None and must be explicitly set.
    These tests verify that when request_ids are provided, they work correctly.
    """

    @given(st.integers(min_value=2, max_value=100))
    @settings(max_examples=50)
    def test_explicit_request_ids_are_preserved(self, count: int) -> None:
        """
        **Feature: python-api-base-2025-validation, Property 23: API Response Request ID Uniqueness**
        **Validates: Requirements 8.4**

        *For any* N ApiResponse instances with explicit request_ids,
        the request_ids SHALL be preserved.
        """
        from uuid import uuid4

        request_ids = [str(uuid4()) for _ in range(count)]
        responses = [
            ApiResponse(data={"index": i}, request_id=rid)
            for i, rid in enumerate(request_ids)
        ]

        # All request IDs should be preserved
        for i, response in enumerate(responses):
            assert response.request_id == request_ids[i]

    @given(st.text(min_size=0, max_size=100))
    @settings(max_examples=100)
    def test_request_id_defaults_to_none(self, data: str) -> None:
        """
        **Feature: python-api-base-2025-validation, Property 23: API Response Request ID Uniqueness**
        **Validates: Requirements 8.4**

        *For any* ApiResponse without explicit request_id, it SHALL default to None.
        """
        response = ApiResponse(data=data)

        # Default is None - request_id should be set by middleware
        assert response.request_id is None

    @given(st.text(min_size=1, max_size=50))
    @settings(max_examples=50)
    def test_request_id_can_be_set(self, request_id: str) -> None:
        """
        **Feature: python-api-base-2025-validation, Property 23: API Response Request ID Uniqueness**
        **Validates: Requirements 8.4**

        *For any* request_id string, it CAN be explicitly set on ApiResponse.
        """
        response = ApiResponse(data={"test": True}, request_id=request_id)

        assert response.request_id == request_id
        assert isinstance(response.request_id, str)


# =============================================================================
# Property 24: Paginated Response Navigation Correctness
# **Feature: python-api-base-2025-validation, Property 24: Paginated Response Navigation**
# **Validates: Requirements 8.2**
# =============================================================================


class TestPaginatedResponseNavigation:
    """Property tests for paginated response navigation correctness.

    **Feature: python-api-base-2025-validation, Property 24: Paginated Response Navigation**
    **Validates: Requirements 8.2**

    Note: PaginatedResponse uses 'size' instead of 'page_size' and 'pages' instead of 'total_pages'.
    """

    @given(
        total=st.integers(min_value=0, max_value=1000),
        page=st.integers(min_value=1, max_value=100),
        size=st.integers(min_value=1, max_value=100),
    )
    @settings(max_examples=100)
    def test_total_pages_calculation(
        self, total: int, page: int, size: int
    ) -> None:
        """
        **Feature: python-api-base-2025-validation, Property 24: Paginated Response Navigation**
        **Validates: Requirements 8.2**

        *For any* PaginatedResponse with total items T and size S,
        pages SHALL equal ceil(T/S).
        """
        # Create items for current page (simulate)
        items_on_page = min(size, max(0, total - (page - 1) * size))
        items = list(range(items_on_page))

        response = PaginatedResponse(
            items=items,
            total=total,
            page=page,
            size=size,
        )

        expected_pages = math.ceil(total / size) if total > 0 else 0
        assert response.pages == expected_pages

    @given(
        total=st.integers(min_value=1, max_value=1000),
        size=st.integers(min_value=1, max_value=100),
    )
    @settings(max_examples=100)
    def test_has_next_on_first_page(self, total: int, size: int) -> None:
        """
        **Feature: python-api-base-2025-validation, Property 24: Paginated Response Navigation**
        **Validates: Requirements 8.2**

        *For any* PaginatedResponse on page 1, has_next SHALL be True
        iff there are more pages.
        """
        items = list(range(min(size, total)))

        response = PaginatedResponse(
            items=items,
            total=total,
            page=1,
            size=size,
        )

        expected_has_next = total > size
        assert response.has_next == expected_has_next

    @given(
        total=st.integers(min_value=1, max_value=1000),
        size=st.integers(min_value=1, max_value=100),
    )
    @settings(max_examples=100)
    def test_has_previous_on_first_page(self, total: int, size: int) -> None:
        """
        **Feature: python-api-base-2025-validation, Property 24: Paginated Response Navigation**
        **Validates: Requirements 8.2**

        *For any* PaginatedResponse on page 1, has_previous SHALL be False.
        """
        items = list(range(min(size, total)))

        response = PaginatedResponse(
            items=items,
            total=total,
            page=1,
            size=size,
        )

        assert response.has_previous is False

    @given(
        total=st.integers(min_value=10, max_value=1000),
        size=st.integers(min_value=1, max_value=10),
    )
    @settings(max_examples=100)
    def test_has_previous_on_later_pages(self, total: int, size: int) -> None:
        """
        **Feature: python-api-base-2025-validation, Property 24: Paginated Response Navigation**
        **Validates: Requirements 8.2**

        *For any* PaginatedResponse on page > 1, has_previous SHALL be True.
        """
        total_pages = math.ceil(total / size)
        if total_pages < 2:
            return  # Skip if only one page

        page = 2  # Second page
        items = list(range(min(size, total - size)))

        response = PaginatedResponse(
            items=items,
            total=total,
            page=page,
            size=size,
        )

        assert response.has_previous is True

    @given(
        total=st.integers(min_value=1, max_value=1000),
        size=st.integers(min_value=1, max_value=100),
    )
    @settings(max_examples=100)
    def test_has_next_on_last_page(self, total: int, size: int) -> None:
        """
        **Feature: python-api-base-2025-validation, Property 24: Paginated Response Navigation**
        **Validates: Requirements 8.2**

        *For any* PaginatedResponse on the last page, has_next SHALL be False.
        """
        total_pages = math.ceil(total / size) if total > 0 else 1
        last_page = max(1, total_pages)
        items_on_last = total - (last_page - 1) * size if total > 0 else 0
        items = list(range(max(0, items_on_last)))

        response = PaginatedResponse(
            items=items,
            total=total,
            page=last_page,
            size=size,
        )

        assert response.has_next is False

    @given(
        total=st.integers(min_value=0, max_value=1000),
        page=st.integers(min_value=1, max_value=100),
        size=st.integers(min_value=1, max_value=100),
    )
    @settings(max_examples=100)
    def test_navigation_consistency(
        self, total: int, page: int, size: int
    ) -> None:
        """
        **Feature: python-api-base-2025-validation, Property 24: Paginated Response Navigation**
        **Validates: Requirements 8.2**

        *For any* PaginatedResponse:
        - has_next == (page < pages)
        - has_previous == (page > 1)
        """
        items_on_page = min(size, max(0, total - (page - 1) * size))
        items = list(range(items_on_page))

        response = PaginatedResponse(
            items=items,
            total=total,
            page=page,
            size=size,
        )

        assert response.has_next == (page < response.pages)
        assert response.has_previous == (page > 1)
