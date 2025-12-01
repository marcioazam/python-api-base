"""Property-based tests for pagination utilities.

**Feature: generic-fastapi-crud, Property 22: Pagination Utility Correctness**
**Validates: Requirements 16.4**
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from my_app.shared.utils.pagination import (
    OffsetPaginationParams,
    decode_cursor,
    encode_cursor,
    paginate_list,
)


class TestOffsetPagination:
    """Property tests for offset pagination."""

    @settings(max_examples=50)
    @given(
        items=st.lists(st.integers(), min_size=0, max_size=100),
        page=st.integers(min_value=1, max_value=20),
        size=st.integers(min_value=1, max_value=50),
    )
    def test_pagination_returns_correct_slice(
        self, items: list[int], page: int, size: int
    ) -> None:
        """
        **Feature: generic-fastapi-crud, Property 22: Pagination Utility Correctness**

        For any list of N items and offset pagination with page and size,
        the utility SHALL return items from index (page-1)*size to min(page*size, N).
        """
        params = OffsetPaginationParams(page=page, size=size)
        result = paginate_list(items, params)

        # Calculate expected slice
        start = (page - 1) * size
        end = min(page * size, len(items))
        expected_items = items[start:end]

        assert list(result.items) == expected_items

    @settings(max_examples=50)
    @given(
        items=st.lists(st.integers(), min_size=0, max_size=100),
        page=st.integers(min_value=1, max_value=20),
        size=st.integers(min_value=1, max_value=50),
    )
    def test_pagination_total_equals_list_length(
        self, items: list[int], page: int, size: int
    ) -> None:
        """
        For any list, pagination total SHALL equal the list length.
        """
        params = OffsetPaginationParams(page=page, size=size)
        result = paginate_list(items, params)

        assert result.total == len(items)

    @settings(max_examples=50)
    @given(
        total=st.integers(min_value=0, max_value=1000),
        page=st.integers(min_value=1, max_value=50),
        size=st.integers(min_value=1, max_value=100),
    )
    def test_pages_calculation(self, total: int, page: int, size: int) -> None:
        """
        For any total and size, pages SHALL equal ceil(total / size).
        """
        items = list(range(total))
        params = OffsetPaginationParams(page=page, size=size)
        result = paginate_list(items, params)

        expected_pages = (total + size - 1) // size if total > 0 else 0
        assert result.pages == expected_pages

    @settings(max_examples=50)
    @given(
        total=st.integers(min_value=1, max_value=100),
        page=st.integers(min_value=1, max_value=20),
        size=st.integers(min_value=1, max_value=50),
    )
    def test_has_next_correctness(self, total: int, page: int, size: int) -> None:
        """
        has_next SHALL be True iff page < pages.
        """
        items = list(range(total))
        params = OffsetPaginationParams(page=page, size=size)
        result = paginate_list(items, params)

        assert result.has_next == (page < result.pages)

    @settings(max_examples=50)
    @given(
        total=st.integers(min_value=1, max_value=100),
        page=st.integers(min_value=1, max_value=20),
        size=st.integers(min_value=1, max_value=50),
    )
    def test_has_previous_correctness(self, total: int, page: int, size: int) -> None:
        """
        has_previous SHALL be True iff page > 1.
        """
        items = list(range(total))
        params = OffsetPaginationParams(page=page, size=size)
        result = paginate_list(items, params)

        assert result.has_previous == (page > 1)

    @settings(max_examples=30)
    @given(
        page=st.integers(max_value=0),
        size=st.integers(min_value=1, max_value=50),
    )
    def test_invalid_page_normalized_to_one(self, page: int, size: int) -> None:
        """
        For any page < 1, params SHALL normalize to page 1.
        """
        params = OffsetPaginationParams(page=page, size=size)
        assert params.page == 1

    @settings(max_examples=30)
    @given(
        page=st.integers(min_value=1, max_value=20),
        size=st.integers(max_value=0),
    )
    def test_invalid_size_normalized_to_one(self, page: int, size: int) -> None:
        """
        For any size < 1, params SHALL normalize to size 1.
        """
        params = OffsetPaginationParams(page=page, size=size)
        assert params.size == 1

    @settings(max_examples=30)
    @given(
        page=st.integers(min_value=1, max_value=20),
        size=st.integers(min_value=101, max_value=500),
    )
    def test_large_size_capped_at_100(self, page: int, size: int) -> None:
        """
        For any size > 100, params SHALL cap at 100.
        """
        params = OffsetPaginationParams(page=page, size=size)
        assert params.size == 100


class TestCursorEncoding:
    """Property tests for cursor encoding."""

    @settings(max_examples=50)
    @given(value=st.text(min_size=1, max_size=100))
    def test_cursor_round_trip(self, value: str) -> None:
        """
        For any string, encoding then decoding SHALL return the original value.
        """
        encoded = encode_cursor(value)
        decoded = decode_cursor(encoded)
        assert decoded == value

    @settings(max_examples=30)
    @given(value=st.text(min_size=1, max_size=100))
    def test_encoded_cursor_is_url_safe(self, value: str) -> None:
        """
        Encoded cursors SHALL be URL-safe (no special characters).
        """
        encoded = encode_cursor(value)
        # URL-safe base64 uses only alphanumeric, -, _, and =
        valid_chars = set(
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_="
        )
        assert all(c in valid_chars for c in encoded)
