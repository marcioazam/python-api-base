"""Property-based tests for Generic CRUD module.

**Feature: generic-fastapi-crud**
"""

from dataclasses import dataclass
from typing import Any

import pytest
from hypothesis import given, settings, strategies as st

from src.my_api.shared.generic_crud.repository import (
    FilterCondition,
    FilterOperator,
    PaginatedResult,
    QueryOptions,
    SortCondition,
)
from src.my_api.shared.generic_crud.service import ServiceResult, ValidationRule


class TestFilterOperator:
    """Property tests for FilterOperator enum."""

    @given(st.sampled_from(list(FilterOperator)))
    @settings(max_examples=100)
    def test_filter_operator_has_string_value(self, operator: FilterOperator) -> None:
        """**Property: All filter operators have string values.**

        **Validates: Requirements 2.1**
        """
        assert isinstance(operator.value, str)
        assert len(operator.value) > 0


class TestFilterCondition:
    """Property tests for FilterCondition dataclass."""

    @given(
        field=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("L", "N"))),
        operator=st.sampled_from(list(FilterOperator)),
        value=st.one_of(st.integers(), st.text(max_size=100), st.booleans()),
        case_sensitive=st.booleans(),
    )
    @settings(max_examples=100)
    def test_filter_condition_creation(self, field: str, operator: FilterOperator, value: Any, case_sensitive: bool) -> None:
        """**Property: FilterCondition can be created with any valid inputs.**

        **Validates: Requirements 2.1, 2.2**
        """
        condition = FilterCondition(field=field, operator=operator, value=value, case_sensitive=case_sensitive)
        assert condition.field == field
        assert condition.operator == operator
        assert condition.value == value
        assert condition.case_sensitive == case_sensitive


class TestSortCondition:
    """Property tests for SortCondition dataclass."""

    @given(
        field=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("L", "N"))),
        ascending=st.booleans(),
    )
    @settings(max_examples=100)
    def test_sort_condition_creation(self, field: str, ascending: bool) -> None:
        """**Property: SortCondition can be created with any valid inputs.**

        **Validates: Requirements 2.5**
        """
        condition = SortCondition(field=field, ascending=ascending)
        assert condition.field == field
        assert condition.ascending == ascending


class TestQueryOptions:
    """Property tests for QueryOptions dataclass."""

    @given(
        limit=st.one_of(st.none(), st.integers(min_value=1, max_value=1000)),
        offset=st.one_of(st.none(), st.integers(min_value=0, max_value=10000)),
    )
    @settings(max_examples=100)
    def test_query_options_pagination(self, limit: int | None, offset: int | None) -> None:
        """**Property: QueryOptions handles pagination parameters correctly.**

        **Validates: Requirements 2.3, 2.4**
        """
        options = QueryOptions(limit=limit, offset=offset)
        assert options.limit == limit
        assert options.offset == offset
        assert isinstance(options.filters, list)
        assert isinstance(options.sorts, list)
        assert isinstance(options.include_relations, list)


class TestPaginatedResult:
    """Property tests for PaginatedResult dataclass."""

    @given(
        total=st.integers(min_value=0, max_value=10000),
        page=st.integers(min_value=1, max_value=100),
        per_page=st.integers(min_value=1, max_value=100),
    )
    @settings(max_examples=100)
    def test_paginated_result_consistency(self, total: int, page: int, per_page: int) -> None:
        """**Property: PaginatedResult has_next and has_prev are consistent with page/total.**

        **Validates: Requirements 2.3, 2.4**
        """
        has_next = page * per_page < total
        has_prev = page > 1

        result = PaginatedResult(
            items=[],
            total=total,
            page=page,
            per_page=per_page,
            has_next=has_next,
            has_prev=has_prev,
        )

        assert result.has_next == (page * per_page < total)
        assert result.has_prev == (page > 1)

    @given(
        items_count=st.integers(min_value=0, max_value=100),
        total=st.integers(min_value=0, max_value=10000),
    )
    @settings(max_examples=100)
    def test_paginated_result_items_count_le_total(self, items_count: int, total: int) -> None:
        """**Property: Items count in a page should be <= total.**

        **Validates: Requirements 2.3**
        """
        items = list(range(min(items_count, total)))
        result = PaginatedResult(
            items=items,
            total=max(total, len(items)),
            page=1,
            per_page=100,
            has_next=False,
            has_prev=False,
        )
        assert len(result.items) <= result.total


class TestServiceResult:
    """Property tests for ServiceResult dataclass."""

    @given(
        success=st.booleans(),
        error=st.one_of(st.none(), st.text(max_size=200)),
    )
    @settings(max_examples=100)
    def test_service_result_creation(self, success: bool, error: str | None) -> None:
        """**Property: ServiceResult can be created with any valid inputs.**

        **Validates: Requirements 1.3, 1.4**
        """
        result = ServiceResult(success=success, error=error)
        assert result.success == success
        assert result.error == error
        assert isinstance(result.errors, list)
        assert isinstance(result.metadata, dict)

    @given(
        data=st.one_of(st.none(), st.integers(), st.text(max_size=100)),
    )
    @settings(max_examples=100)
    def test_service_result_with_data(self, data: Any) -> None:
        """**Property: ServiceResult can hold any data type.**

        **Validates: Requirements 1.1**
        """
        result = ServiceResult(success=True, data=data)
        assert result.data == data


class TestValidationRule:
    """Property tests for ValidationRule dataclass."""

    @given(
        field=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("L", "N"))),
        message=st.text(min_size=1, max_size=200),
    )
    @settings(max_examples=100)
    def test_validation_rule_creation(self, field: str, message: str) -> None:
        """**Property: ValidationRule can be created with any valid inputs.**

        **Validates: Requirements 3.1, 3.2**
        """
        rule = ValidationRule(field=field, validator=lambda x: True, message=message)
        assert rule.field == field
        assert rule.message == message
        assert callable(rule.validator)
        assert rule.validator(None) is True


class TestFilterOperatorCoverage:
    """Property tests for filter operator coverage."""

    def test_all_operators_have_unique_values(self) -> None:
        """**Property: All filter operators have unique string values.**

        **Validates: Requirements 2.1**
        """
        values = [op.value for op in FilterOperator]
        assert len(values) == len(set(values))

    def test_comparison_operators_exist(self) -> None:
        """**Property: Standard comparison operators exist.**

        **Validates: Requirements 2.1**
        """
        required_ops = {"eq", "ne", "gt", "gte", "lt", "lte"}
        actual_ops = {op.value for op in FilterOperator}
        assert required_ops.issubset(actual_ops)

    def test_collection_operators_exist(self) -> None:
        """**Property: Collection operators exist.**

        **Validates: Requirements 2.2**
        """
        required_ops = {"in", "not_in"}
        actual_ops = {op.value for op in FilterOperator}
        assert required_ops.issubset(actual_ops)

    def test_string_operators_exist(self) -> None:
        """**Property: String operators exist.**

        **Validates: Requirements 2.2**
        """
        required_ops = {"like", "ilike"}
        actual_ops = {op.value for op in FilterOperator}
        assert required_ops.issubset(actual_ops)

    def test_null_operators_exist(self) -> None:
        """**Property: Null check operators exist.**

        **Validates: Requirements 2.2**
        """
        required_ops = {"is_null", "is_not_null"}
        actual_ops = {op.value for op in FilterOperator}
        assert required_ops.issubset(actual_ops)
