"""Tests for trace context processors module.

Tests for add_trace_context, add_dapr_context, get_trace_context_processors.
"""

import logging
from unittest.mock import MagicMock

from core.shared.logging.trace_context import (
    add_dapr_context,
    add_trace_context,
    get_trace_context_processors,
)


class TestAddTraceContext:
    """Tests for add_trace_context processor."""

    def test_returns_event_dict(self) -> None:
        """Processor should return event dict."""
        logger = MagicMock(spec=logging.Logger)
        event_dict = {"event": "test"}
        result = add_trace_context(logger, "info", event_dict)
        assert result is event_dict

    def test_preserves_existing_keys(self) -> None:
        """Processor should preserve existing event dict keys."""
        logger = MagicMock(spec=logging.Logger)
        event_dict = {"event": "test", "level": "info", "custom": "value"}
        result = add_trace_context(logger, "info", event_dict)
        assert result["event"] == "test"
        assert result["level"] == "info"
        assert result["custom"] == "value"

    def test_handles_empty_event_dict(self) -> None:
        """Processor should handle empty event dict."""
        logger = MagicMock(spec=logging.Logger)
        event_dict: dict = {}
        result = add_trace_context(logger, "info", event_dict)
        assert isinstance(result, dict)

    def test_handles_various_method_names(self) -> None:
        """Processor should work with various method names."""
        logger = MagicMock(spec=logging.Logger)
        for method in ["debug", "info", "warning", "error", "critical"]:
            event_dict = {"event": "test"}
            result = add_trace_context(logger, method, event_dict)
            assert result is event_dict


class TestAddDaprContext:
    """Tests for add_dapr_context processor."""

    def test_returns_event_dict(self) -> None:
        """Processor should return event dict."""
        logger = MagicMock(spec=logging.Logger)
        event_dict = {"event": "test"}
        result = add_dapr_context(logger, "info", event_dict)
        assert result is event_dict

    def test_preserves_existing_keys(self) -> None:
        """Processor should preserve existing event dict keys."""
        logger = MagicMock(spec=logging.Logger)
        event_dict = {"event": "test", "level": "info"}
        result = add_dapr_context(logger, "info", event_dict)
        assert result["event"] == "test"
        assert result["level"] == "info"

    def test_handles_empty_event_dict(self) -> None:
        """Processor should handle empty event dict."""
        logger = MagicMock(spec=logging.Logger)
        event_dict: dict = {}
        result = add_dapr_context(logger, "info", event_dict)
        assert isinstance(result, dict)

    def test_handles_various_method_names(self) -> None:
        """Processor should work with various method names."""
        logger = MagicMock(spec=logging.Logger)
        for method in ["debug", "info", "warning", "error"]:
            event_dict = {"event": "test"}
            result = add_dapr_context(logger, method, event_dict)
            assert result is event_dict


class TestGetTraceContextProcessors:
    """Tests for get_trace_context_processors function."""

    def test_returns_list(self) -> None:
        """Function should return a list."""
        result = get_trace_context_processors()
        assert isinstance(result, list)

    def test_contains_both_processors(self) -> None:
        """Function should return both processors."""
        result = get_trace_context_processors()
        assert add_trace_context in result
        assert add_dapr_context in result

    def test_returns_two_processors(self) -> None:
        """Function should return exactly two processors."""
        result = get_trace_context_processors()
        assert len(result) == 2

    def test_processors_are_callable(self) -> None:
        """All processors should be callable."""
        result = get_trace_context_processors()
        for processor in result:
            assert callable(processor)
