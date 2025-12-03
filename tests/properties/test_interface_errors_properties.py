"""Property-based tests for interface errors module.

**Feature: interface-modules-workflow-analysis**
**Validates: Requirements 2.1, 2.3, 2.5**
"""

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from interface.errors import (
    InterfaceError,
    ValidationError,
    FieldError,
    NotFoundError,
    UnwrapError,
    BuilderValidationError,
    InvalidStatusTransitionError,
    TransformationError,
    ConfigurationError,
    ErrorCode,
    ErrorMessage,
)
from interface.errors.exceptions import (
    CompositionError,
    RepositoryError,
    ServiceError,
)


# =============================================================================
# Strategies
# =============================================================================

error_code_strategy = st.sampled_from(list(ErrorCode))

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

message_strategy = st.text(min_size=1, max_size=200)

field_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L",)),
    min_size=1,
    max_size=30,
)


# =============================================================================
# Property 1: Error Hierarchy Inheritance
# =============================================================================


class TestErrorHierarchyInheritance:
    """Property tests for error hierarchy.

    **Feature: interface-modules-workflow-analysis, Property 1: Error Hierarchy Inheritance**
    **Validates: Requirements 2.1**
    """

    def test_all_errors_inherit_from_interface_error(self) -> None:
        """For any error class in the errors module, it SHALL inherit from InterfaceError."""
        error_classes = [
            ValidationError,
            NotFoundError,
            UnwrapError,
            BuilderValidationError,
            InvalidStatusTransitionError,
            TransformationError,
            ConfigurationError,
            CompositionError,
            RepositoryError,
            ServiceError,
        ]

        for error_class in error_classes:
            assert issubclass(error_class, InterfaceError), (
                f"{error_class.__name__} should inherit from InterfaceError"
            )

    @given(resource=resource_strategy, id=id_strategy)
    @settings(max_examples=100)
    def test_not_found_error_is_interface_error(self, resource: str, id: str) -> None:
        """NotFoundError instances are InterfaceError instances."""
        assume(len(resource.strip()) > 0 and len(id.strip()) > 0)
        error = NotFoundError(resource, id)
        assert isinstance(error, InterfaceError)
        assert isinstance(error, Exception)

    @given(
        field=field_strategy,
        message=message_strategy,
        code=st.text(min_size=1, max_size=20),
    )
    @settings(max_examples=100)
    def test_validation_error_is_interface_error(
        self, field: str, message: str, code: str
    ) -> None:
        """ValidationError instances are InterfaceError instances."""
        assume(len(field.strip()) > 0)
        field_error = FieldError(field, message, code)
        error = ValidationError([field_error])
        assert isinstance(error, InterfaceError)


# =============================================================================
# Property 2: ErrorMessage Factory Methods Produce Valid Codes
# =============================================================================


class TestErrorMessageFactoryMethods:
    """Property tests for ErrorMessage factory methods.

    **Feature: interface-modules-workflow-analysis, Property 2: ErrorMessage Factory Methods Produce Valid Codes**
    **Validates: Requirements 2.3**
    """

    @given(resource=resource_strategy, id=id_strategy)
    @settings(max_examples=100)
    def test_not_found_produces_not_found_code(self, resource: str, id: str) -> None:
        """not_found factory produces NOT_FOUND code."""
        assume(len(resource.strip()) > 0 and len(id.strip()) > 0)
        error = ErrorMessage.not_found(resource, id)
        assert error.code == ErrorCode.NOT_FOUND

    @given(field=field_strategy, reason=message_strategy)
    @settings(max_examples=100)
    def test_validation_error_produces_validation_code(
        self, field: str, reason: str
    ) -> None:
        """validation_error factory produces VALIDATION_ERROR code."""
        assume(len(field.strip()) > 0)
        error = ErrorMessage.validation_error(field, reason)
        assert error.code == ErrorCode.VALIDATION_ERROR

    @given(reason=message_strategy)
    @settings(max_examples=100)
    def test_unauthorized_produces_unauthorized_code(self, reason: str) -> None:
        """unauthorized factory produces UNAUTHORIZED code."""
        error = ErrorMessage.unauthorized(reason)
        assert error.code == ErrorCode.UNAUTHORIZED

    @given(resource=resource_strategy, action=message_strategy)
    @settings(max_examples=100)
    def test_forbidden_produces_forbidden_code(
        self, resource: str, action: str
    ) -> None:
        """forbidden factory produces FORBIDDEN code."""
        assume(len(resource.strip()) > 0)
        error = ErrorMessage.forbidden(resource, action)
        assert error.code == ErrorCode.FORBIDDEN

    @given(resource=resource_strategy, reason=message_strategy)
    @settings(max_examples=100)
    def test_conflict_produces_conflict_code(self, resource: str, reason: str) -> None:
        """conflict factory produces CONFLICT code."""
        assume(len(resource.strip()) > 0)
        error = ErrorMessage.conflict(resource, reason)
        assert error.code == ErrorCode.CONFLICT

    @given(context=message_strategy)
    @settings(max_examples=100)
    def test_internal_error_produces_internal_code(self, context: str) -> None:
        """internal_error factory produces INTERNAL_ERROR code."""
        error = ErrorMessage.internal_error(context)
        assert error.code == ErrorCode.INTERNAL_ERROR

    @given(
        operation=resource_strategy,
        duration_ms=st.integers(min_value=1, max_value=100000),
    )
    @settings(max_examples=100)
    def test_timeout_produces_timeout_code(
        self, operation: str, duration_ms: int
    ) -> None:
        """timeout factory produces TIMEOUT code."""
        assume(len(operation.strip()) > 0)
        error = ErrorMessage.timeout(operation, duration_ms)
        assert error.code == ErrorCode.TIMEOUT

    @given(
        limit=st.integers(min_value=1, max_value=10000),
        window_seconds=st.integers(min_value=1, max_value=3600),
    )
    @settings(max_examples=100)
    def test_rate_limited_produces_rate_limited_code(
        self, limit: int, window_seconds: int
    ) -> None:
        """rate_limited factory produces RATE_LIMITED code."""
        error = ErrorMessage.rate_limited(limit, window_seconds)
        assert error.code == ErrorCode.RATE_LIMITED

    @given(reason=message_strategy)
    @settings(max_examples=100)
    def test_bad_request_produces_bad_request_code(self, reason: str) -> None:
        """bad_request factory produces BAD_REQUEST code."""
        error = ErrorMessage.bad_request(reason)
        assert error.code == ErrorCode.BAD_REQUEST

    @given(service=resource_strategy)
    @settings(max_examples=100)
    def test_service_unavailable_produces_service_unavailable_code(
        self, service: str
    ) -> None:
        """service_unavailable factory produces SERVICE_UNAVAILABLE code."""
        assume(len(service.strip()) > 0)
        error = ErrorMessage.service_unavailable(service)
        assert error.code == ErrorCode.SERVICE_UNAVAILABLE


# =============================================================================
# Property 3: RFC 7807 Problem Details Format
# =============================================================================


class TestRFC7807ProblemDetails:
    """Property tests for RFC 7807 Problem Details format.

    **Feature: interface-modules-workflow-analysis, Property 3: RFC 7807 Problem Details Format**
    **Validates: Requirements 2.5**
    """

    @given(code=error_code_strategy, message=message_strategy)
    @settings(max_examples=100)
    def test_problem_details_has_required_fields(
        self, code: ErrorCode, message: str
    ) -> None:
        """to_problem_details SHALL produce dict with type, title, status, detail."""
        error = ErrorMessage(code=code, message=message)
        problem = error.to_problem_details()

        assert "type" in problem
        assert "title" in problem
        assert "status" in problem
        assert "detail" in problem

    @given(code=error_code_strategy, message=message_strategy)
    @settings(max_examples=100)
    def test_problem_details_status_is_integer(
        self, code: ErrorCode, message: str
    ) -> None:
        """status field SHALL be an integer HTTP status code."""
        error = ErrorMessage(code=code, message=message)
        problem = error.to_problem_details()

        assert isinstance(problem["status"], int)
        assert 100 <= problem["status"] <= 599

    @given(
        code=error_code_strategy,
        message=message_strategy,
        type_uri=st.text(min_size=1, max_size=100),
    )
    @settings(max_examples=100)
    def test_problem_details_preserves_type_uri(
        self, code: ErrorCode, message: str, type_uri: str
    ) -> None:
        """type_uri parameter SHALL be preserved in output."""
        assume(len(type_uri.strip()) > 0)
        error = ErrorMessage(code=code, message=message)
        problem = error.to_problem_details(type_uri=type_uri)

        assert problem["type"] == type_uri

    @given(
        code=error_code_strategy,
        message=message_strategy,
        instance=st.text(min_size=1, max_size=100),
    )
    @settings(max_examples=100)
    def test_problem_details_includes_instance_when_provided(
        self, code: ErrorCode, message: str, instance: str
    ) -> None:
        """instance parameter SHALL be included when provided."""
        assume(len(instance.strip()) > 0)
        error = ErrorMessage(code=code, message=message)
        problem = error.to_problem_details(instance=instance)

        assert "instance" in problem
        assert problem["instance"] == instance


# =============================================================================
# Property 4: ErrorMessage to_dict Round Trip
# =============================================================================


class TestErrorMessageToDict:
    """Property tests for ErrorMessage to_dict.

    **Feature: interface-modules-workflow-analysis, Property 4: ErrorMessage to_dict Round Trip**
    **Validates: Requirements 2.3**
    """

    @given(code=error_code_strategy, message=message_strategy)
    @settings(max_examples=100)
    def test_to_dict_contains_code_and_message(
        self, code: ErrorCode, message: str
    ) -> None:
        """to_dict SHALL return dict with code and message."""
        error = ErrorMessage(code=code, message=message)
        result = error.to_dict()

        assert "code" in result
        assert "message" in result
        assert result["code"] == code.value
        assert result["message"] == message

    @given(
        code=error_code_strategy,
        message=message_strategy,
        details=st.dictionaries(
            keys=st.text(min_size=1, max_size=20),
            values=st.text(min_size=1, max_size=50),
            min_size=1,
            max_size=5,
        ),
    )
    @settings(max_examples=100)
    def test_to_dict_includes_details_when_present(
        self, code: ErrorCode, message: str, details: dict
    ) -> None:
        """to_dict SHALL include details when present."""
        error = ErrorMessage(code=code, message=message, details=details)
        result = error.to_dict()

        assert "details" in result
        assert result["details"] == details


# =============================================================================
# Property 5: HTTP Status Code Mapping
# =============================================================================


class TestHTTPStatusCodeMapping:
    """Property tests for HTTP status code mapping.

    **Feature: interface-modules-workflow-analysis, Property 5: HTTP Status Code Mapping**
    **Validates: Requirements 2.5**
    """

    def test_not_found_maps_to_404(self) -> None:
        """NOT_FOUND SHALL map to HTTP 404."""
        error = ErrorMessage(code=ErrorCode.NOT_FOUND, message="test")
        problem = error.to_problem_details()
        assert problem["status"] == 404

    def test_validation_error_maps_to_400(self) -> None:
        """VALIDATION_ERROR SHALL map to HTTP 400."""
        error = ErrorMessage(code=ErrorCode.VALIDATION_ERROR, message="test")
        problem = error.to_problem_details()
        assert problem["status"] == 400

    def test_unauthorized_maps_to_401(self) -> None:
        """UNAUTHORIZED SHALL map to HTTP 401."""
        error = ErrorMessage(code=ErrorCode.UNAUTHORIZED, message="test")
        problem = error.to_problem_details()
        assert problem["status"] == 401

    def test_forbidden_maps_to_403(self) -> None:
        """FORBIDDEN SHALL map to HTTP 403."""
        error = ErrorMessage(code=ErrorCode.FORBIDDEN, message="test")
        problem = error.to_problem_details()
        assert problem["status"] == 403

    def test_conflict_maps_to_409(self) -> None:
        """CONFLICT SHALL map to HTTP 409."""
        error = ErrorMessage(code=ErrorCode.CONFLICT, message="test")
        problem = error.to_problem_details()
        assert problem["status"] == 409

    def test_internal_error_maps_to_500(self) -> None:
        """INTERNAL_ERROR SHALL map to HTTP 500."""
        error = ErrorMessage(code=ErrorCode.INTERNAL_ERROR, message="test")
        problem = error.to_problem_details()
        assert problem["status"] == 500

    def test_timeout_maps_to_504(self) -> None:
        """TIMEOUT SHALL map to HTTP 504."""
        error = ErrorMessage(code=ErrorCode.TIMEOUT, message="test")
        problem = error.to_problem_details()
        assert problem["status"] == 504

    def test_rate_limited_maps_to_429(self) -> None:
        """RATE_LIMITED SHALL map to HTTP 429."""
        error = ErrorMessage(code=ErrorCode.RATE_LIMITED, message="test")
        problem = error.to_problem_details()
        assert problem["status"] == 429

    def test_bad_request_maps_to_400(self) -> None:
        """BAD_REQUEST SHALL map to HTTP 400."""
        error = ErrorMessage(code=ErrorCode.BAD_REQUEST, message="test")
        problem = error.to_problem_details()
        assert problem["status"] == 400

    def test_service_unavailable_maps_to_503(self) -> None:
        """SERVICE_UNAVAILABLE SHALL map to HTTP 503."""
        error = ErrorMessage(code=ErrorCode.SERVICE_UNAVAILABLE, message="test")
        problem = error.to_problem_details()
        assert problem["status"] == 503


# =============================================================================
# Property 19: FieldError to_dict Completeness
# =============================================================================


class TestFieldErrorToDict:
    """Property tests for FieldError to_dict.

    **Feature: interface-modules-workflow-analysis, Property 19: FieldError to_dict Completeness**
    **Validates: Requirements 2.1**
    """

    @given(
        field=field_strategy,
        message=message_strategy,
        code=st.text(min_size=1, max_size=20),
    )
    @settings(max_examples=100)
    def test_to_dict_contains_all_fields(
        self, field: str, message: str, code: str
    ) -> None:
        """to_dict SHALL return dict with field, message, and code keys."""
        assume(len(field.strip()) > 0 and len(code.strip()) > 0)
        error = FieldError(field, message, code)
        result = error.to_dict()

        assert "field" in result
        assert "message" in result
        assert "code" in result
        assert result["field"] == field
        assert result["message"] == message
        assert result["code"] == code


# =============================================================================
# Property 20: ValidationError Error Count
# =============================================================================


class TestValidationErrorCount:
    """Property tests for ValidationError error count.

    **Feature: interface-modules-workflow-analysis, Property 20: ValidationError Error Count**
    **Validates: Requirements 2.1**
    """

    @given(
        errors=st.lists(
            st.tuples(field_strategy, message_strategy, st.text(min_size=1, max_size=20)),
            min_size=1,
            max_size=10,
        )
    )
    @settings(max_examples=100)
    def test_errors_list_has_correct_count(
        self, errors: list[tuple[str, str, str]]
    ) -> None:
        """ValidationError errors list SHALL have exactly N elements."""
        field_errors = [
            FieldError(field, message, code)
            for field, message, code in errors
            if len(field.strip()) > 0 and len(code.strip()) > 0
        ]
        assume(len(field_errors) > 0)

        validation_error = ValidationError(field_errors)
        assert len(validation_error.errors) == len(field_errors)
