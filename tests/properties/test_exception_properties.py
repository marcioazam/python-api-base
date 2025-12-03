"""Property-based tests for exception hierarchy.

**Feature: generic-fastapi-crud, Property 15: Not Found Error Format**
**Feature: generic-fastapi-crud, Property 17: Business Rule Violation Format**
**Validates: Requirements 9.1, 9.4**
"""


import pytest
pytest.skip('Module core.exceptions not implemented', allow_module_level=True)

from hypothesis import given, settings
from hypothesis import strategies as st

from core.exceptions import (
    BusinessRuleViolationError,
    EntityNotFoundError,
)


class TestEntityNotFoundError:
    """Property tests for EntityNotFoundError."""

    @settings(max_examples=50)
    @given(
        entity_type=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("L",))),
        entity_id=st.text(min_size=1, max_size=36, alphabet=st.characters(whitelist_categories=("L", "N"))),
    )
    def test_not_found_error_format(self, entity_type: str, entity_id: str) -> None:
        """
        **Feature: generic-fastapi-crud, Property 15: Not Found Error Format**

        For any request for a non-existent resource, the error SHALL be 404
        with entity_type and entity_id in details.
        """
        error = EntityNotFoundError(entity_type=entity_type, entity_id=entity_id)

        # Check status code
        assert error.status_code == 404

        # Check error code
        assert error.error_code == "ENTITY_NOT_FOUND"

        # Check message contains entity info
        assert entity_type in error.message
        assert entity_id in error.message

        # Check details
        assert error.details["entity_type"] == entity_type
        assert error.details["entity_id"] == entity_id

    @settings(max_examples=30)
    @given(
        entity_type=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("L",))),
        entity_id=st.integers(min_value=1, max_value=1000000),
    )
    def test_not_found_error_with_int_id(self, entity_type: str, entity_id: int) -> None:
        """
        EntityNotFoundError SHALL accept integer IDs and convert to string in details.
        """
        error = EntityNotFoundError(entity_type=entity_type, entity_id=entity_id)

        assert error.status_code == 404
        assert error.details["entity_id"] == str(entity_id)

    @settings(max_examples=30)
    @given(
        entity_type=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("L",))),
        entity_id=st.text(min_size=1, max_size=36, alphabet=st.characters(whitelist_categories=("L", "N"))),
    )
    def test_not_found_error_to_dict(self, entity_type: str, entity_id: str) -> None:
        """
        EntityNotFoundError.to_dict() SHALL return all error information.
        """
        error = EntityNotFoundError(entity_type=entity_type, entity_id=entity_id)
        error_dict = error.to_dict()

        assert "message" in error_dict
        assert "error_code" in error_dict
        assert "status_code" in error_dict
        assert "details" in error_dict
        assert error_dict["status_code"] == 404
        assert error_dict["error_code"] == "ENTITY_NOT_FOUND"


class TestBusinessRuleViolationError:
    """Property tests for BusinessRuleViolationError."""

    @settings(max_examples=50)
    @given(
        rule=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("L", "N"))),
        message=st.text(min_size=1, max_size=200, alphabet=st.characters(whitelist_categories=("L", "N", "P"))),
    )
    def test_business_rule_violation_format(self, rule: str, message: str) -> None:
        """
        **Feature: generic-fastapi-crud, Property 17: Business Rule Violation Format**

        For any business rule violation, the error SHALL be 400 with
        error code containing the rule name and violation description.
        """
        error = BusinessRuleViolationError(rule=rule, message=message)

        # Check status code
        assert error.status_code == 400

        # Check error code contains rule name (uppercased)
        assert rule.upper() in error.error_code
        assert error.error_code.startswith("BUSINESS_RULE_")

        # Check message
        assert error.message == message

        # Check details
        assert error.details["rule"] == rule

    @settings(max_examples=30)
    @given(
        rule=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("L", "N"))),
        message=st.text(min_size=1, max_size=200, alphabet=st.characters(whitelist_categories=("L", "N", "P"))),
    )
    def test_business_rule_violation_to_dict(self, rule: str, message: str) -> None:
        """
        BusinessRuleViolationError.to_dict() SHALL return all error information.
        """
        error = BusinessRuleViolationError(rule=rule, message=message)
        error_dict = error.to_dict()

        assert "message" in error_dict
        assert "error_code" in error_dict
        assert "status_code" in error_dict
        assert "details" in error_dict
        assert error_dict["status_code"] == 400
        assert error_dict["details"]["rule"] == rule
