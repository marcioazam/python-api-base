"""Tests for correlation ID module.

Tests for correlation ID generation, context management, and propagation.
"""

from datetime import UTC, datetime

import pytest

from infrastructure.observability.correlation_id import (
    CorrelationConfig,
    CorrelationContext,
    CorrelationContextManager,
    CorrelationService,
    IdFormat,
    add_correlation_context,
    clear_context,
    create_correlation_service,
    generate_id,
    get_correlation_id,
    get_current_context,
    get_parent_span_id,
    get_request_id,
    get_span_id,
    propagate_correlation,
    set_correlation_id,
    set_parent_span_id,
    set_request_id,
    set_span_id,
    with_correlation,
)


class TestIdFormat:
    """Tests for IdFormat enum."""

    def test_uuid4_value(self) -> None:
        """UUID4 should have correct value."""
        assert IdFormat.UUID4.value == "uuid4"

    def test_uuid4_hex_value(self) -> None:
        """UUID4_HEX should have correct value."""
        assert IdFormat.UUID4_HEX.value == "uuid4_hex"

    def test_short_value(self) -> None:
        """SHORT should have correct value."""
        assert IdFormat.SHORT.value == "short"

    def test_timestamp_value(self) -> None:
        """TIMESTAMP should have correct value."""
        assert IdFormat.TIMESTAMP.value == "timestamp"


class TestGenerateId:
    """Tests for generate_id function."""

    def test_uuid4_format(self) -> None:
        """UUID4 format should include dashes."""
        id_val = generate_id(IdFormat.UUID4)
        assert "-" in id_val
        assert len(id_val) == 36

    def test_uuid4_hex_format(self) -> None:
        """UUID4_HEX format should be 32 chars without dashes."""
        id_val = generate_id(IdFormat.UUID4_HEX)
        assert "-" not in id_val
        assert len(id_val) == 32

    def test_short_format(self) -> None:
        """SHORT format should be 16 chars."""
        id_val = generate_id(IdFormat.SHORT)
        assert len(id_val) == 16

    def test_timestamp_format(self) -> None:
        """TIMESTAMP format should include timestamp prefix."""
        id_val = generate_id(IdFormat.TIMESTAMP)
        assert "-" in id_val
        # Format: YYYYMMDDHHMMSS-xxxxxxxxxxxx
        parts = id_val.split("-")
        assert len(parts[0]) == 14  # Timestamp part

    def test_default_format(self) -> None:
        """Default format should be UUID4_HEX."""
        id_val = generate_id()
        assert len(id_val) == 32

    def test_generates_unique_ids(self) -> None:
        """Should generate unique IDs."""
        ids = {generate_id() for _ in range(100)}
        assert len(ids) == 100


class TestContextVars:
    """Tests for context variable functions."""

    def setup_method(self) -> None:
        """Clear context before each test."""
        clear_context()

    def test_get_correlation_id_default(self) -> None:
        """get_correlation_id should return None by default."""
        assert get_correlation_id() is None

    def test_set_and_get_correlation_id(self) -> None:
        """set_correlation_id and get_correlation_id should work together."""
        set_correlation_id("test-corr-id")
        assert get_correlation_id() == "test-corr-id"

    def test_get_request_id_default(self) -> None:
        """get_request_id should return None by default."""
        assert get_request_id() is None

    def test_set_and_get_request_id(self) -> None:
        """set_request_id and get_request_id should work together."""
        set_request_id("test-req-id")
        assert get_request_id() == "test-req-id"

    def test_get_span_id_default(self) -> None:
        """get_span_id should return None by default."""
        assert get_span_id() is None

    def test_set_and_get_span_id(self) -> None:
        """set_span_id and get_span_id should work together."""
        set_span_id("test-span-id")
        assert get_span_id() == "test-span-id"

    def test_get_parent_span_id_default(self) -> None:
        """get_parent_span_id should return None by default."""
        assert get_parent_span_id() is None

    def test_set_and_get_parent_span_id(self) -> None:
        """set_parent_span_id and get_parent_span_id should work together."""
        set_parent_span_id("test-parent-span")
        assert get_parent_span_id() == "test-parent-span"

    def test_clear_context(self) -> None:
        """clear_context should clear all context vars."""
        set_correlation_id("corr")
        set_request_id("req")
        set_span_id("span")
        set_parent_span_id("parent")

        clear_context()

        assert get_correlation_id() is None
        assert get_request_id() is None
        assert get_span_id() is None
        assert get_parent_span_id() is None


class TestCorrelationContext:
    """Tests for CorrelationContext dataclass."""

    def test_init_required_fields(self) -> None:
        """CorrelationContext should store required fields."""
        ctx = CorrelationContext(
            correlation_id="corr-123",
            request_id="req-456",
        )
        assert ctx.correlation_id == "corr-123"
        assert ctx.request_id == "req-456"

    def test_init_optional_fields(self) -> None:
        """CorrelationContext should store optional fields."""
        ctx = CorrelationContext(
            correlation_id="corr",
            request_id="req",
            span_id="span",
            parent_span_id="parent",
            trace_id="trace",
            service_name="my-service",
        )
        assert ctx.span_id == "span"
        assert ctx.parent_span_id == "parent"
        assert ctx.trace_id == "trace"
        assert ctx.service_name == "my-service"

    def test_to_dict_basic(self) -> None:
        """to_dict should include required fields."""
        ctx = CorrelationContext(correlation_id="corr", request_id="req")
        d = ctx.to_dict()
        assert d["correlation_id"] == "corr"
        assert d["request_id"] == "req"

    def test_to_dict_with_optional(self) -> None:
        """to_dict should include optional fields when set."""
        ctx = CorrelationContext(
            correlation_id="corr",
            request_id="req",
            span_id="span",
            trace_id="trace",
        )
        d = ctx.to_dict()
        assert d["span_id"] == "span"
        assert d["trace_id"] == "trace"

    def test_to_headers_basic(self) -> None:
        """to_headers should return HTTP headers."""
        ctx = CorrelationContext(correlation_id="corr", request_id="req")
        headers = ctx.to_headers()
        assert headers["X-Correlation-ID"] == "corr"
        assert headers["X-Request-ID"] == "req"

    def test_to_headers_with_optional(self) -> None:
        """to_headers should include optional headers when set."""
        ctx = CorrelationContext(
            correlation_id="corr",
            request_id="req",
            span_id="span",
            trace_id="trace",
        )
        headers = ctx.to_headers()
        assert headers["X-Span-ID"] == "span"
        assert headers["X-Trace-ID"] == "trace"

    def test_from_headers(self) -> None:
        """from_headers should create context from headers."""
        headers = {
            "X-Correlation-ID": "corr-from-header",
            "X-Request-ID": "req-from-header",
        }
        ctx = CorrelationContext.from_headers(headers)
        assert ctx.correlation_id == "corr-from-header"
        assert ctx.request_id == "req-from-header"

    def test_from_headers_generates_missing(self) -> None:
        """from_headers should generate missing IDs."""
        ctx = CorrelationContext.from_headers({})
        assert ctx.correlation_id != ""
        assert ctx.request_id != ""

    def test_from_headers_no_generate(self) -> None:
        """from_headers should not generate when disabled."""
        ctx = CorrelationContext.from_headers({}, generate_missing=False)
        assert ctx.correlation_id == ""
        assert ctx.request_id == ""

    def test_create_new(self) -> None:
        """create_new should create context with generated IDs."""
        ctx = CorrelationContext.create_new()
        assert ctx.correlation_id != ""
        assert ctx.request_id != ""
        assert ctx.span_id is not None

    def test_create_new_with_service_name(self) -> None:
        """create_new should set service name."""
        ctx = CorrelationContext.create_new(service_name="my-service")
        assert ctx.service_name == "my-service"


class TestCorrelationContextManager:
    """Tests for CorrelationContextManager."""

    def setup_method(self) -> None:
        """Clear context before each test."""
        clear_context()

    def test_sets_context_on_enter(self) -> None:
        """Context manager should set context vars on enter."""
        ctx = CorrelationContext(correlation_id="corr", request_id="req")
        with CorrelationContextManager(ctx):
            assert get_correlation_id() == "corr"
            assert get_request_id() == "req"

    def test_clears_context_on_exit(self) -> None:
        """Context manager should restore context on exit."""
        ctx = CorrelationContext(correlation_id="corr", request_id="req")
        with CorrelationContextManager(ctx):
            pass
        # Context should be restored (to None in this case)
        assert get_correlation_id() is None

    def test_creates_new_context_if_none(self) -> None:
        """Context manager should create new context if none provided."""
        with CorrelationContextManager() as ctx:
            assert ctx.correlation_id != ""
            assert get_correlation_id() == ctx.correlation_id


class TestGetCurrentContext:
    """Tests for get_current_context function."""

    def setup_method(self) -> None:
        """Clear context before each test."""
        clear_context()

    def test_returns_none_when_empty(self) -> None:
        """get_current_context should return None when no context set."""
        assert get_current_context() is None

    def test_returns_context_when_set(self) -> None:
        """get_current_context should return context when set."""
        set_correlation_id("corr")
        set_request_id("req")
        ctx = get_current_context()
        assert ctx is not None
        assert ctx.correlation_id == "corr"
        assert ctx.request_id == "req"


class TestDecorators:
    """Tests for correlation decorators."""

    def setup_method(self) -> None:
        """Clear context before each test."""
        clear_context()

    def test_with_correlation_sets_context(self) -> None:
        """with_correlation should set context during function execution."""
        captured_id = None

        @with_correlation(correlation_id="test-corr")
        def my_func() -> None:
            nonlocal captured_id
            captured_id = get_correlation_id()

        my_func()
        assert captured_id == "test-corr"

    def test_propagate_correlation_creates_child_span(self) -> None:
        """propagate_correlation should create child span."""
        set_correlation_id("parent-corr")
        set_request_id("parent-req")
        set_span_id("parent-span")

        captured_parent = None

        @propagate_correlation
        def my_func() -> None:
            nonlocal captured_parent
            captured_parent = get_parent_span_id()

        my_func()
        assert captured_parent == "parent-span"


class TestAddCorrelationContext:
    """Tests for add_correlation_context structlog processor."""

    def setup_method(self) -> None:
        """Clear context before each test."""
        clear_context()

    def test_adds_correlation_id(self) -> None:
        """Processor should add correlation_id to event dict."""
        set_correlation_id("test-corr")
        event_dict: dict = {}
        result = add_correlation_context(None, "info", event_dict)
        assert result["correlation_id"] == "test-corr"

    def test_adds_request_id(self) -> None:
        """Processor should add request_id to event dict."""
        set_request_id("test-req")
        event_dict: dict = {}
        result = add_correlation_context(None, "info", event_dict)
        assert result["request_id"] == "test-req"

    def test_adds_span_id(self) -> None:
        """Processor should add span_id to event dict."""
        set_span_id("test-span")
        event_dict: dict = {}
        result = add_correlation_context(None, "info", event_dict)
        assert result["span_id"] == "test-span"


class TestCorrelationConfig:
    """Tests for CorrelationConfig dataclass."""

    def test_default_values(self) -> None:
        """Config should have sensible defaults."""
        config = CorrelationConfig()
        assert config.header_name == "X-Correlation-ID"
        assert config.request_id_header == "X-Request-ID"
        assert config.generate_if_missing is True
        assert config.id_format == IdFormat.UUID4_HEX
        assert config.propagate_to_response is True

    def test_custom_values(self) -> None:
        """Config should accept custom values."""
        config = CorrelationConfig(
            header_name="X-Custom-ID",
            generate_if_missing=False,
            service_name="my-service",
        )
        assert config.header_name == "X-Custom-ID"
        assert config.generate_if_missing is False
        assert config.service_name == "my-service"


class TestCorrelationService:
    """Tests for CorrelationService class."""

    def test_extract_from_headers(self) -> None:
        """extract_from_headers should create context from headers."""
        service = CorrelationService()
        headers = {"X-Correlation-ID": "corr", "X-Request-ID": "req"}
        ctx = service.extract_from_headers(headers)
        assert ctx.correlation_id == "corr"

    def test_create_context(self) -> None:
        """create_context should create new context."""
        service = CorrelationService()
        ctx = service.create_context()
        assert ctx.correlation_id != ""

    def test_get_response_headers(self) -> None:
        """get_response_headers should return headers."""
        service = CorrelationService()
        ctx = CorrelationContext(correlation_id="corr", request_id="req")
        headers = service.get_response_headers(ctx)
        assert headers["X-Correlation-ID"] == "corr"

    def test_get_response_headers_disabled(self) -> None:
        """get_response_headers should return empty when disabled."""
        config = CorrelationConfig(propagate_to_response=False)
        service = CorrelationService(config)
        ctx = CorrelationContext(correlation_id="corr", request_id="req")
        headers = service.get_response_headers(ctx)
        assert headers == {}

    def test_bind_context(self) -> None:
        """bind_context should return context manager."""
        service = CorrelationService()
        ctx = CorrelationContext(correlation_id="corr", request_id="req")
        manager = service.bind_context(ctx)
        assert isinstance(manager, CorrelationContextManager)


class TestCreateCorrelationService:
    """Tests for create_correlation_service factory."""

    def test_creates_service(self) -> None:
        """create_correlation_service should create service."""
        service = create_correlation_service()
        assert isinstance(service, CorrelationService)

    def test_creates_service_with_config(self) -> None:
        """create_correlation_service should accept config."""
        config = CorrelationConfig(service_name="test")
        service = create_correlation_service(config)
        assert service._config.service_name == "test"
