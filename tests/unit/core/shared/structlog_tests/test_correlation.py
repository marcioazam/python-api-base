"""Unit tests for correlation ID management.

**Feature: observability-infrastructure**
**Requirement: R1.2 - Correlation ID Propagation**
"""

import pytest

from core.shared.logging.correlation import (
    generate_correlation_id,
    get_correlation_id,
    set_correlation_id,
    clear_correlation_id,
    bind_contextvars,
    clear_contextvars,
)


class TestCorrelationId:
    """Tests for correlation ID functions."""

    def test_generate_correlation_id(self) -> None:
        """Test correlation ID generation."""
        cid = generate_correlation_id()

        assert cid is not None
        assert len(cid) == 36  # UUID format
        assert "-" in cid

    def test_generate_unique_ids(self) -> None:
        """Test that generated IDs are unique."""
        ids = [generate_correlation_id() for _ in range(100)]

        assert len(set(ids)) == 100

    def test_set_and_get_correlation_id(self) -> None:
        """Test setting and getting correlation ID."""
        clear_correlation_id()

        cid = set_correlation_id("test-123")

        assert cid == "test-123"
        assert get_correlation_id() == "test-123"

    def test_set_generates_id_when_none(self) -> None:
        """Test that set_correlation_id generates ID when None."""
        clear_correlation_id()

        cid = set_correlation_id(None)

        assert cid is not None
        assert len(cid) == 36
        assert get_correlation_id() == cid

    def test_clear_correlation_id(self) -> None:
        """Test clearing correlation ID."""
        set_correlation_id("test-123")
        clear_correlation_id()

        assert get_correlation_id() is None

    def test_get_returns_none_when_not_set(self) -> None:
        """Test get returns None when not set."""
        clear_correlation_id()

        assert get_correlation_id() is None


class TestContextvars:
    """Tests for context variable binding."""

    def test_bind_contextvars(self) -> None:
        """Test binding context variables."""
        clear_contextvars()
        bind_contextvars(user_id="123", tenant_id="acme")

        # Variables should be bound (verified through structlog)
        # This test mainly verifies no exceptions are raised

    def test_clear_contextvars(self) -> None:
        """Test clearing context variables."""
        bind_contextvars(user_id="123")
        clear_contextvars()

        # Should not raise
