"""Property-based tests for Rate Limiter.

**Feature: api-architecture-analysis**
**Validates: Requirements 6.5**
"""

from unittest.mock import MagicMock

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from starlette.requests import Request
from starlette.datastructures import Headers

from my_app.adapters.api.middleware.rate_limiter import (
    get_client_ip,
    rate_limit_exceeded_handler,
)
from my_app.application.common.dto import ProblemDetail


# Generators for IP addresses
@st.composite
def ipv4_addresses(draw: st.DrawFn) -> str:
    """Generate valid IPv4 addresses."""
    octets = [draw(st.integers(min_value=0, max_value=255)) for _ in range(4)]
    return ".".join(str(o) for o in octets)


@st.composite
def forwarded_for_headers(draw: st.DrawFn) -> str:
    """Generate X-Forwarded-For header values with multiple IPs."""
    num_ips = draw(st.integers(min_value=1, max_value=5))
    ips = [draw(ipv4_addresses()) for _ in range(num_ips)]
    return ", ".join(ips)


class TestGetClientIp:
    """Property tests for client IP extraction.
    
    **Feature: api-architecture-analysis**
    **Validates: Requirements 6.5**
    """

    @given(ip=ipv4_addresses())
    @settings(max_examples=100)
    def test_extracts_first_ip_from_forwarded_header(self, ip: str) -> None:
        """
        For any X-Forwarded-For header, the first IP SHALL be extracted.
        """
        # Create mock request with X-Forwarded-For header
        mock_request = MagicMock(spec=Request)
        mock_request.headers = Headers({"X-Forwarded-For": ip})
        
        result = get_client_ip(mock_request)
        
        assert result == ip

    @given(forwarded=forwarded_for_headers())
    @settings(max_examples=100)
    def test_extracts_first_ip_from_multiple_forwarded(self, forwarded: str) -> None:
        """
        For any X-Forwarded-For header with multiple IPs, only the first SHALL be returned.
        """
        mock_request = MagicMock(spec=Request)
        mock_request.headers = Headers({"X-Forwarded-For": forwarded})
        
        result = get_client_ip(mock_request)
        expected_first_ip = forwarded.split(",")[0].strip()
        
        assert result == expected_first_ip


class TestRateLimitResponseFormat:
    """Property tests for rate limit response format.
    
    **Feature: api-architecture-analysis, Property 14: Rate Limit Response Format**
    **Validates: Requirements 6.5**
    """

    @given(
        url=st.text(min_size=1, max_size=100).map(lambda x: f"http://test.com/{x}"),
        detail_message=st.text(min_size=1, max_size=200),
    )
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_rate_limit_response_follows_rfc7807(
        self,
        url: str,
        detail_message: str,
    ) -> None:
        """
        **Feature: api-architecture-analysis, Property 14: Rate Limit Response Format**
        **Validates: Requirements 6.5**
        
        For any rate limit exceeded response, the body SHALL follow RFC 7807
        Problem Details format with required fields.
        """
        # Create mock request
        mock_request = MagicMock(spec=Request)
        mock_request.url = MagicMock()
        mock_request.url.__str__ = MagicMock(return_value=url)
        
        # Create mock exception
        mock_exc = MagicMock()
        mock_exc.detail = detail_message
        
        # Call handler
        response = await rate_limit_exceeded_handler(mock_request, mock_exc)
        
        # Verify status code
        assert response.status_code == 429
        
        # Verify RFC 7807 fields in body
        body = response.body.decode()
        assert "type" in body
        assert "title" in body
        assert "status" in body
        assert "429" in body
        assert "RATE_LIMIT_EXCEEDED" in body

    @given(retry_after=st.integers(min_value=1, max_value=3600))
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_rate_limit_response_includes_retry_after_header(
        self,
        retry_after: int,
    ) -> None:
        """
        **Feature: api-architecture-analysis, Property 14: Rate Limit Response Format**
        **Validates: Requirements 6.5**
        
        For any rate limit exceeded response, the Retry-After header SHALL be present.
        """
        mock_request = MagicMock(spec=Request)
        mock_request.url = MagicMock()
        mock_request.url.__str__ = MagicMock(return_value="http://test.com/api")
        
        mock_exc = MagicMock()
        mock_exc.detail = "Rate limit exceeded"
        
        response = await rate_limit_exceeded_handler(mock_request, mock_exc)
        
        # Verify Retry-After header is present
        assert "Retry-After" in response.headers
        
        # Verify it's a valid integer
        retry_value = response.headers["Retry-After"]
        assert retry_value.isdigit()
        assert int(retry_value) > 0


class TestProblemDetailFormat:
    """Property tests for ProblemDetail RFC 7807 compliance.
    
    **Feature: api-architecture-analysis, Property 7: ProblemDetail RFC 7807 Compliance**
    **Validates: Requirements 4.4**
    """

    @given(
        status=st.integers(min_value=100, max_value=599),
        title=st.text(min_size=1, max_size=100),
        detail=st.text(min_size=0, max_size=500),
    )
    @settings(max_examples=100)
    def test_problem_detail_has_required_fields(
        self,
        status: int,
        title: str,
        detail: str,
    ) -> None:
        """
        **Feature: api-architecture-analysis, Property 7: ProblemDetail RFC 7807 Compliance**
        **Validates: Requirements 4.4**
        
        For any ProblemDetail, the fields type, title, and status SHALL be present
        and status SHALL be a valid HTTP status code (100-599).
        """
        problem = ProblemDetail(
            type="https://api.example.com/errors/TEST",
            title=title,
            status=status,
            detail=detail if detail else None,
        )
        
        # Verify required fields
        assert problem.type is not None
        assert problem.title is not None
        assert problem.status is not None
        
        # Verify status is valid HTTP code
        assert 100 <= problem.status <= 599

    @given(
        error_code=st.text(
            alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="_"),
            min_size=1,
            max_size=50,
        ),
    )
    @settings(max_examples=100)
    def test_problem_detail_type_is_uri(
        self,
        error_code: str,
    ) -> None:
        """
        For any ProblemDetail, the type field SHALL be a valid URI reference.
        """
        problem = ProblemDetail(
            type=f"https://api.example.com/errors/{error_code}",
            title="Test Error",
            status=400,
        )
        
        # Verify type starts with valid URI scheme
        assert problem.type.startswith("https://") or problem.type.startswith("http://") or problem.type == "about:blank"

    @given(
        errors=st.lists(
            st.fixed_dictionaries({
                "field": st.text(min_size=1, max_size=50),
                "message": st.text(min_size=1, max_size=200),
                "code": st.text(min_size=1, max_size=50),
            }),
            min_size=0,
            max_size=10,
        ),
    )
    @settings(max_examples=100)
    def test_problem_detail_errors_list_format(
        self,
        errors: list[dict],
    ) -> None:
        """
        For any ProblemDetail with validation errors, the errors field SHALL
        contain a list of error objects with field, message, and code.
        """
        problem = ProblemDetail(
            type="https://api.example.com/errors/VALIDATION_ERROR",
            title="Validation Error",
            status=422,
            errors=errors if errors else None,
        )
        
        if problem.errors:
            for error in problem.errors:
                assert "field" in error
                assert "message" in error
                assert "code" in error
