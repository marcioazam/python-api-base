"""Integration tests for error handling module.

**Feature: interface-modules-integration**
**Validates: Requirements 5.1, 5.2, 5.3, 5.4**
"""

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st


# =============================================================================
# Strategies for Property Tests
# =============================================================================

resource_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N")),
    min_size=1,
    max_size=50,
)

id_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "Nd")),
    min_size=1,
    max_size=36,
)

field_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L",)),
    min_size=1,
    max_size=30,
)

message_strategy = st.text(min_size=1, max_size=200)

code_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N")),
    min_size=1,
    max_size=20,
)


# =============================================================================
# Property 10: NotFoundError Contains Resource Info
# =============================================================================


class TestNotFoundErrorResourceInfo:
    """Property tests for NotFoundError resource information.

    **Feature: interface-modules-integration, Property 10: NotFoundError Contains Resource Info**
    **Validates: Requirements 5.1**
    """

    @given(resource=resource_strategy, id=id_strategy)
    @settings(max_examples=100)
    def test_not_found_error_contains_resource(self, resource: str, id: str) -> None:
        """NotFoundError SHALL contain resource type in attributes."""
        assume(len(resource.strip()) > 0 and len(id.strip()) > 0)
        
        from interface.errors import NotFoundError
        
        error = NotFoundError(resource, id)
        
        assert hasattr(error, "resource")
        assert error.resource == resource

    @given(resource=resource_strategy, id=id_strategy)
    @settings(max_examples=100)
    def test_not_found_error_contains_id(self, resource: str, id: str) -> None:
        """NotFoundError SHALL contain resource ID in attributes."""
        assume(len(resource.strip()) > 0 and len(id.strip()) > 0)
        
        from interface.errors import NotFoundError
        
        error = NotFoundError(resource, id)
        
        assert hasattr(error, "id")
        assert error.id == id

    @given(resource=resource_strategy, id=id_strategy)
    @settings(max_examples=100)
    def test_not_found_error_message_contains_info(self, resource: str, id: str) -> None:
        """NotFoundError message SHALL contain resource and ID."""
        assume(len(resource.strip()) > 0 and len(id.strip()) > 0)
        
        from interface.errors import NotFoundError
        
        error = NotFoundError(resource, id)
        
        assert resource in str(error)
        assert id in str(error)

    def test_not_found_error_is_interface_error(self) -> None:
        """NotFoundError SHALL inherit from InterfaceError."""
        from interface.errors import NotFoundError, InterfaceError
        
        error = NotFoundError("TestResource", "test-id")
        
        assert isinstance(error, InterfaceError)
        assert isinstance(error, Exception)


# =============================================================================
# Property 11: ValidationError Contains Field Errors
# =============================================================================


class TestValidationErrorFieldErrors:
    """Property tests for ValidationError field errors.

    **Feature: interface-modules-integration, Property 11: ValidationError Contains Field Errors**
    **Validates: Requirements 5.2**
    """

    @given(field=field_strategy, message=message_strategy, code=code_strategy)
    @settings(max_examples=100)
    def test_field_error_contains_field_name(self, field: str, message: str, code: str) -> None:
        """FieldError SHALL contain field name."""
        assume(len(field.strip()) > 0 and len(code.strip()) > 0)
        
        from interface.errors import FieldError
        
        error = FieldError(field, message, code)
        
        assert hasattr(error, "field")
        assert error.field == field

    @given(field=field_strategy, message=message_strategy, code=code_strategy)
    @settings(max_examples=100)
    def test_field_error_contains_message(self, field: str, message: str, code: str) -> None:
        """FieldError SHALL contain error message."""
        assume(len(field.strip()) > 0 and len(code.strip()) > 0)
        
        from interface.errors import FieldError
        
        error = FieldError(field, message, code)
        
        assert hasattr(error, "message")
        assert error.message == message

    @given(field=field_strategy, message=message_strategy, code=code_strategy)
    @settings(max_examples=100)
    def test_field_error_contains_code(self, field: str, message: str, code: str) -> None:
        """FieldError SHALL contain error code."""
        assume(len(field.strip()) > 0 and len(code.strip()) > 0)
        
        from interface.errors import FieldError
        
        error = FieldError(field, message, code)
        
        assert hasattr(error, "code")
        assert error.code == code

    @given(
        errors=st.lists(
            st.tuples(field_strategy, message_strategy, code_strategy),
            min_size=1,
            max_size=5,
        )
    )
    @settings(max_examples=100)
    def test_validation_error_contains_field_errors(
        self, errors: list[tuple[str, str, str]]
    ) -> None:
        """ValidationError SHALL contain list of FieldError objects."""
        from interface.errors import ValidationError, FieldError
        
        field_errors = [
            FieldError(field, message, code)
            for field, message, code in errors
            if len(field.strip()) > 0 and len(code.strip()) > 0
        ]
        assume(len(field_errors) > 0)
        
        validation_error = ValidationError(field_errors)
        
        assert hasattr(validation_error, "errors")
        assert len(validation_error.errors) == len(field_errors)

    def test_validation_error_is_interface_error(self) -> None:
        """ValidationError SHALL inherit from InterfaceError."""
        from interface.errors import ValidationError, FieldError, InterfaceError
        
        field_error = FieldError("test_field", "test message", "TEST_CODE")
        error = ValidationError([field_error])
        
        assert isinstance(error, InterfaceError)
        assert isinstance(error, Exception)


# =============================================================================
# Additional Error Integration Tests
# =============================================================================


class TestErrorMessageRFC7807:
    """Tests for ErrorMessage RFC 7807 compliance.

    **Feature: interface-modules-integration**
    **Validates: Requirements 5.3, 5.4**
    """

    def test_error_message_to_problem_details_has_type(self) -> None:
        """to_problem_details SHALL include type field."""
        from interface.errors import ErrorMessage, ErrorCode
        
        error = ErrorMessage(code=ErrorCode.NOT_FOUND, message="Test error")
        problem = error.to_problem_details()
        
        assert "type" in problem

    def test_error_message_to_problem_details_has_title(self) -> None:
        """to_problem_details SHALL include title field."""
        from interface.errors import ErrorMessage, ErrorCode
        
        error = ErrorMessage(code=ErrorCode.NOT_FOUND, message="Test error")
        problem = error.to_problem_details()
        
        assert "title" in problem

    def test_error_message_to_problem_details_has_status(self) -> None:
        """to_problem_details SHALL include status field."""
        from interface.errors import ErrorMessage, ErrorCode
        
        error = ErrorMessage(code=ErrorCode.NOT_FOUND, message="Test error")
        problem = error.to_problem_details()
        
        assert "status" in problem
        assert isinstance(problem["status"], int)

    def test_error_message_to_problem_details_has_detail(self) -> None:
        """to_problem_details SHALL include detail field."""
        from interface.errors import ErrorMessage, ErrorCode
        
        error = ErrorMessage(code=ErrorCode.NOT_FOUND, message="Test error")
        problem = error.to_problem_details()
        
        assert "detail" in problem
        assert problem["detail"] == "Test error"

    def test_error_message_with_details_has_extensions(self) -> None:
        """to_problem_details SHALL include extensions when details present."""
        from interface.errors import ErrorMessage, ErrorCode
        
        details = {"resource": "Item", "id": "123"}
        error = ErrorMessage(code=ErrorCode.NOT_FOUND, message="Test error", details=details)
        problem = error.to_problem_details()
        
        assert "extensions" in problem
        assert problem["extensions"] == details


class TestErrorCodeMapping:
    """Tests for ErrorCode to HTTP status mapping.

    **Feature: interface-modules-integration**
    **Validates: Requirements 5.3**
    """

    def test_not_found_maps_to_404(self) -> None:
        """NOT_FOUND SHALL map to HTTP 404."""
        from interface.errors import ErrorMessage, ErrorCode
        
        error = ErrorMessage(code=ErrorCode.NOT_FOUND, message="test")
        problem = error.to_problem_details()
        
        assert problem["status"] == 404

    def test_validation_error_maps_to_400(self) -> None:
        """VALIDATION_ERROR SHALL map to HTTP 400."""
        from interface.errors import ErrorMessage, ErrorCode
        
        error = ErrorMessage(code=ErrorCode.VALIDATION_ERROR, message="test")
        problem = error.to_problem_details()
        
        assert problem["status"] == 400

    def test_unauthorized_maps_to_401(self) -> None:
        """UNAUTHORIZED SHALL map to HTTP 401."""
        from interface.errors import ErrorMessage, ErrorCode
        
        error = ErrorMessage(code=ErrorCode.UNAUTHORIZED, message="test")
        problem = error.to_problem_details()
        
        assert problem["status"] == 401

    def test_forbidden_maps_to_403(self) -> None:
        """FORBIDDEN SHALL map to HTTP 403."""
        from interface.errors import ErrorMessage, ErrorCode
        
        error = ErrorMessage(code=ErrorCode.FORBIDDEN, message="test")
        problem = error.to_problem_details()
        
        assert problem["status"] == 403

    def test_internal_error_maps_to_500(self) -> None:
        """INTERNAL_ERROR SHALL map to HTTP 500."""
        from interface.errors import ErrorMessage, ErrorCode
        
        error = ErrorMessage(code=ErrorCode.INTERNAL_ERROR, message="test")
        problem = error.to_problem_details()
        
        assert problem["status"] == 500
