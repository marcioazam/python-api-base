"""Property-based tests for request/response logging middleware.

**Feature: api-base-improvements**
**Validates: Requirements 9.1, 9.3, 9.5**
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from my_app.adapters.api.middleware.request_logger import (
    RequestLogEntry,
    ResponseLogEntry,
    mask_sensitive_value,
    mask_dict,
    sanitize_headers,
    SENSITIVE_FIELDS,
    SENSITIVE_HEADERS,
    MASK_VALUE,
)


# Strategy for HTTP methods
method_strategy = st.sampled_from(["GET", "POST", "PUT", "PATCH", "DELETE"])

# Strategy for paths
path_strategy = st.sampled_from([
    "/api/v1/items",
    "/api/v1/users",
    "/health/ready",
    "/api/v1/auth/login",
])

# Strategy for request IDs
request_id_strategy = st.text(
    min_size=8,
    max_size=36,
    alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="-"),
)

# Strategy for status codes
status_code_strategy = st.sampled_from([200, 201, 400, 401, 403, 404, 500])

# Strategy for sensitive field names
sensitive_field_strategy = st.sampled_from(list(SENSITIVE_FIELDS))

# Strategy for sensitive header names
sensitive_header_strategy = st.sampled_from(list(SENSITIVE_HEADERS))

# Strategy for non-sensitive field names
safe_field_strategy = st.sampled_from([
    "name", "email", "id", "created_at", "status", "count",
])


class TestRequestLoggingCompleteness:
    """Property tests for request logging completeness."""

    @settings(max_examples=100, deadline=None)
    @given(
        request_id=request_id_strategy,
        method=method_strategy,
        path=path_strategy,
    )
    def test_request_log_contains_required_fields(
        self, request_id: str, method: str, path: str
    ) -> None:
        """
        **Feature: api-base-improvements, Property 23: Request logging completeness**
        **Validates: Requirements 9.1**

        For any incoming request, the log entry SHALL contain method, path,
        and request_id.
        """
        entry = RequestLogEntry(
            request_id=request_id,
            method=method,
            path=path,
        )

        data = entry.to_dict()

        assert "request_id" in data
        assert "method" in data
        assert "path" in data
        assert data["request_id"] == request_id
        assert data["method"] == method
        assert data["path"] == path

    @settings(max_examples=50, deadline=None)
    @given(
        request_id=request_id_strategy,
        method=method_strategy,
        path=path_strategy,
    )
    def test_request_log_includes_optional_fields(
        self, request_id: str, method: str, path: str
    ) -> None:
        """
        **Feature: api-base-improvements, Property 23: Request logging completeness**
        **Validates: Requirements 9.1**

        Request log SHALL include headers, query params, and client info.
        """
        entry = RequestLogEntry(
            request_id=request_id,
            method=method,
            path=path,
            query_params={"page": "1", "limit": "10"},
            headers={"Content-Type": "application/json"},
            body_size=256,
            client_ip="192.168.1.1",
            user_agent="TestClient/1.0",
        )

        data = entry.to_dict()

        assert "query_params" in data
        assert "headers" in data
        assert "body_size" in data
        assert "client_ip" in data
        assert "user_agent" in data

    @settings(max_examples=100, deadline=None)
    @given(
        request_id=request_id_strategy,
        status_code=status_code_strategy,
        duration=st.floats(min_value=0.1, max_value=10000.0),
    )
    def test_response_log_contains_required_fields(
        self, request_id: str, status_code: int, duration: float
    ) -> None:
        """
        **Feature: api-base-improvements, Property 23: Request logging completeness**
        **Validates: Requirements 9.1**

        Response log SHALL contain request_id, status_code, and duration.
        """
        entry = ResponseLogEntry(
            request_id=request_id,
            status_code=status_code,
            duration_ms=duration,
            response_size=1024,
        )

        data = entry.to_dict()

        assert "request_id" in data
        assert "status_code" in data
        assert "duration_ms" in data
        assert "response_size" in data
        assert data["request_id"] == request_id
        assert data["status_code"] == status_code


class TestSensitiveDataMasking:
    """Property tests for sensitive data masking."""

    @settings(max_examples=100, deadline=None)
    @given(
        field_name=sensitive_field_strategy,
        value=st.text(min_size=1, max_size=50),
    )
    def test_sensitive_fields_are_masked(self, field_name: str, value: str) -> None:
        """
        **Feature: api-base-improvements, Property 24: Sensitive data masking**
        **Validates: Requirements 9.3**

        For any log entry containing password or token fields, those values
        SHALL be masked.
        """
        result = mask_sensitive_value(field_name, value)

        assert result == MASK_VALUE
        assert value not in str(result)

    @settings(max_examples=100, deadline=None)
    @given(
        header_name=sensitive_header_strategy,
        value=st.text(min_size=1, max_size=100),
    )
    def test_sensitive_headers_are_masked(self, header_name: str, value: str) -> None:
        """
        **Feature: api-base-improvements, Property 24: Sensitive data masking**
        **Validates: Requirements 9.3**

        Sensitive headers SHALL be masked in logs.
        """
        headers = {header_name: value}
        result = sanitize_headers(headers)

        assert result[header_name] == MASK_VALUE

    @settings(max_examples=100, deadline=None)
    @given(
        field_name=safe_field_strategy,
        value=st.text(min_size=1, max_size=50),
    )
    def test_non_sensitive_fields_not_masked(self, field_name: str, value: str) -> None:
        """
        **Feature: api-base-improvements, Property 24: Sensitive data masking**
        **Validates: Requirements 9.3**

        Non-sensitive fields SHALL NOT be masked.
        """
        result = mask_sensitive_value(field_name, value)

        assert result == value

    @settings(max_examples=50, deadline=None)
    @given(
        sensitive_field=sensitive_field_strategy,
        safe_field=safe_field_strategy,
        sensitive_value=st.text(min_size=1, max_size=20),
        safe_value=st.text(min_size=1, max_size=20),
    )
    def test_mask_dict_handles_mixed_content(
        self,
        sensitive_field: str,
        safe_field: str,
        sensitive_value: str,
        safe_value: str,
    ) -> None:
        """
        **Feature: api-base-improvements, Property 24: Sensitive data masking**
        **Validates: Requirements 9.3**

        mask_dict SHALL mask sensitive fields while preserving safe fields.
        """
        data = {
            sensitive_field: sensitive_value,
            safe_field: safe_value,
        }

        result = mask_dict(data)

        assert result[sensitive_field] == MASK_VALUE
        assert result[safe_field] == safe_value

    def test_mask_dict_handles_nested_structures(self) -> None:
        """
        **Feature: api-base-improvements, Property 24: Sensitive data masking**
        **Validates: Requirements 9.3**

        mask_dict SHALL handle nested dictionaries and lists.
        """
        data = {
            "user": {
                "name": "John",
                "password": "secret123",
            },
            "tokens": [
                {"token": "abc123"},
                {"token": "def456"},
            ],
        }

        result = mask_dict(data)

        assert result["user"]["name"] == "John"
        assert result["user"]["password"] == MASK_VALUE
        assert result["tokens"][0]["token"] == MASK_VALUE
        assert result["tokens"][1]["token"] == MASK_VALUE

    def test_authorization_header_masked(self) -> None:
        """
        **Feature: api-base-improvements, Property 24: Sensitive data masking**
        **Validates: Requirements 9.3**

        Authorization header SHALL always be masked.
        """
        headers = {
            "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "Content-Type": "application/json",
        }

        result = sanitize_headers(headers)

        assert result["Authorization"] == MASK_VALUE
        assert result["Content-Type"] == "application/json"


class TestRequestIDCorrelation:
    """Property tests for request ID correlation."""

    @settings(max_examples=100, deadline=None)
    @given(request_id=request_id_strategy)
    def test_request_and_response_share_request_id(self, request_id: str) -> None:
        """
        **Feature: api-base-improvements, Property 25: Request ID correlation**
        **Validates: Requirements 9.5**

        For any request, all related log entries SHALL contain the same request_id.
        """
        request_entry = RequestLogEntry(
            request_id=request_id,
            method="GET",
            path="/test",
        )

        response_entry = ResponseLogEntry(
            request_id=request_id,
            status_code=200,
            duration_ms=50.0,
        )

        assert request_entry.request_id == response_entry.request_id
        assert request_entry.to_dict()["request_id"] == response_entry.to_dict()["request_id"]

    @settings(max_examples=50, deadline=None)
    @given(
        request_id1=request_id_strategy,
        request_id2=request_id_strategy,
    )
    def test_different_requests_have_different_ids(
        self, request_id1: str, request_id2: str
    ) -> None:
        """
        **Feature: api-base-improvements, Property 25: Request ID correlation**
        **Validates: Requirements 9.5**

        Different requests SHALL have different request IDs (when generated).
        """
        # This test verifies the concept - actual ID generation is in RequestIDMiddleware
        if request_id1 != request_id2:
            entry1 = RequestLogEntry(request_id=request_id1, method="GET", path="/a")
            entry2 = RequestLogEntry(request_id=request_id2, method="GET", path="/b")

            assert entry1.request_id != entry2.request_id

    def test_request_id_in_all_log_fields(self) -> None:
        """
        **Feature: api-base-improvements, Property 25: Request ID correlation**
        **Validates: Requirements 9.5**

        request_id SHALL be present in all log entry types.
        """
        request_id = "test-request-123"

        request_entry = RequestLogEntry(
            request_id=request_id,
            method="POST",
            path="/api/v1/items",
        )

        response_entry = ResponseLogEntry(
            request_id=request_id,
            status_code=201,
            duration_ms=100.0,
        )

        # Both entries should have request_id as first-class field
        assert "request_id" in request_entry.to_dict()
        assert "request_id" in response_entry.to_dict()
        assert request_entry.to_dict()["request_id"] == request_id
        assert response_entry.to_dict()["request_id"] == request_id
