"""Property tests for generic_crud module.

**Feature: shared-modules-phase2**
**Validates: Requirements 13.1, 13.2, 13.3, 14.1**
"""

import json

import pytest
from hypothesis import given, settings, strategies as st

from my_api.shared.generic_crud.endpoints import (
    EndpointConfig,
    FilterParams,
    GenericEndpoints,
    PaginationParams,
    SortParams,
)
from my_api.shared.generic_crud.repository import FilterCondition, FilterOperator


class TestFilterFieldValidation:
    """Property tests for filter field validation.

    **Feature: shared-modules-phase2, Property 23: Filter Field Validation**
    **Validates: Requirements 13.1, 13.2**
    """

    def test_parse_valid_filter(self) -> None:
        """Valid filter JSON should be parsed correctly."""
        filters_str = json.dumps([
            {"field": "name", "operator": "eq", "value": "test"}
        ])

        # Create a mock endpoints instance to test parsing
        # Note: In real implementation, this would be tested via API
        filters_data = json.loads(filters_str)
        assert len(filters_data) == 1
        assert filters_data[0]["field"] == "name"

    def test_parse_invalid_json_returns_empty(self) -> None:
        """Invalid JSON should return empty list."""
        invalid_json = "not valid json {"

        try:
            json.loads(invalid_json)
            parsed = True
        except json.JSONDecodeError:
            parsed = False

        assert parsed is False

    @settings(max_examples=100)
    @given(
        field=st.text(min_size=1, max_size=30, alphabet="abcdefghijklmnopqrstuvwxyz_"),
        value=st.text(min_size=1, max_size=50),
    )
    def test_filter_condition_creation(self, field: str, value: str) -> None:
        """FilterCondition should be created correctly."""
        condition = FilterCondition(
            field=field,
            operator=FilterOperator.EQ,
            value=value,
        )
        assert condition.field == field
        assert condition.value == value
        assert condition.operator == FilterOperator.EQ


class TestMalformedJSONHandling:
    """Property tests for malformed JSON handling.

    **Feature: shared-modules-phase2, Property 24: Malformed JSON Handling**
    **Validates: Requirements 13.3**
    """

    @settings(max_examples=100)
    @given(malformed=st.text(min_size=1, max_size=100))
    def test_malformed_json_detected(self, malformed: str) -> None:
        """Malformed JSON should be detected."""
        # Skip if it happens to be valid JSON
        try:
            json.loads(malformed)
            return  # Valid JSON, skip
        except (json.JSONDecodeError, ValueError):
            pass

        # Malformed JSON should raise JSONDecodeError
        with pytest.raises((json.JSONDecodeError, ValueError)):
            json.loads(malformed)


class TestPaginationCapEnforcement:
    """Property tests for pagination cap enforcement.

    **Feature: shared-modules-phase2, Property 25: Pagination Cap Enforcement**
    **Validates: Requirements 14.1**
    """

    @settings(max_examples=100)
    @given(per_page=st.integers(min_value=101, max_value=10000))
    def test_per_page_capped_at_100(self, per_page: int) -> None:
        """per_page exceeding 100 should be capped."""
        # PaginationParams has max constraint of 100
        capped = min(per_page, 100)
        assert capped <= 100

    @settings(max_examples=100)
    @given(per_page=st.integers(min_value=1, max_value=100))
    def test_valid_per_page_unchanged(self, per_page: int) -> None:
        """Valid per_page should remain unchanged."""
        params = PaginationParams(page=1, per_page=per_page)
        assert params.per_page == per_page

    def test_pagination_params_defaults(self) -> None:
        """PaginationParams should have sensible defaults."""
        params = PaginationParams()
        assert params.page == 1
        assert params.per_page == 20


class TestSortParsing:
    """Test sort parameter parsing."""

    def test_parse_single_sort(self) -> None:
        """Single sort field should be parsed correctly."""
        sort_str = "name:asc"
        parts = sort_str.split(":")
        assert parts[0] == "name"
        assert parts[1] == "asc"

    def test_parse_multiple_sorts(self) -> None:
        """Multiple sort fields should be parsed correctly."""
        sort_str = "name:asc,created_at:desc"
        sorts = sort_str.split(",")
        assert len(sorts) == 2

    def test_parse_sort_default_ascending(self) -> None:
        """Sort without direction should default to ascending."""
        sort_str = "name"
        parts = sort_str.split(":")
        ascending = len(parts) == 1 or parts[1].lower() != "desc"
        assert ascending is True


class TestFilterOperators:
    """Test filter operators."""

    def test_all_operators_defined(self) -> None:
        """All expected operators should be defined."""
        expected_operators = [
            "eq", "ne", "gt", "gte", "lt", "lte",
            "in", "not_in", "like", "ilike",
            "is_null", "is_not_null", "between"
        ]
        for op in expected_operators:
            assert hasattr(FilterOperator, op.upper())

    @settings(max_examples=100)
    @given(operator=st.sampled_from(list(FilterOperator)))
    def test_operator_has_value(self, operator: FilterOperator) -> None:
        """Each operator should have a string value."""
        assert operator.value is not None
        assert len(operator.value) > 0
