"""Tests for event sourcing snapshots module.

Tests for Snapshot class.
"""

from datetime import UTC, datetime

import pytest

from infrastructure.db.event_sourcing.snapshots import Snapshot


class TestSnapshot:
    """Tests for Snapshot class."""

    def test_init_with_required_fields(self) -> None:
        """Snapshot should initialize with required fields."""
        snapshot = Snapshot(
            aggregate_id="agg-123",
            aggregate_type="User",
            version=5,
            state={"name": "John"},
        )
        assert snapshot.aggregate_id == "agg-123"
        assert snapshot.aggregate_type == "User"
        assert snapshot.version == 5
        assert snapshot.state == {"name": "John"}

    def test_init_default_state_hash(self) -> None:
        """Snapshot should have empty state_hash by default."""
        snapshot = Snapshot(
            aggregate_id="agg-123",
            aggregate_type="User",
            version=5,
            state={},
        )
        assert snapshot.state_hash == ""

    def test_init_default_created_at(self) -> None:
        """Snapshot should have created_at timestamp."""
        snapshot = Snapshot(
            aggregate_id="agg-123",
            aggregate_type="User",
            version=5,
            state={},
        )
        assert snapshot.created_at is not None
        assert isinstance(snapshot.created_at, datetime)

    def test_init_custom_state_hash(self) -> None:
        """Snapshot should accept custom state_hash."""
        snapshot = Snapshot(
            aggregate_id="agg-123",
            aggregate_type="User",
            version=5,
            state={},
            state_hash="abc123",
        )
        assert snapshot.state_hash == "abc123"

    def test_compute_hash_deterministic(self) -> None:
        """_compute_hash should be deterministic."""
        state = {"name": "John", "age": 30}
        hash1 = Snapshot._compute_hash(state)
        hash2 = Snapshot._compute_hash(state)
        assert hash1 == hash2

    def test_compute_hash_different_for_different_state(self) -> None:
        """_compute_hash should produce different hashes for different states."""
        hash1 = Snapshot._compute_hash({"name": "John"})
        hash2 = Snapshot._compute_hash({"name": "Jane"})
        assert hash1 != hash2

    def test_compute_hash_order_independent(self) -> None:
        """_compute_hash should be order-independent for dict keys."""
        hash1 = Snapshot._compute_hash({"a": 1, "b": 2})
        hash2 = Snapshot._compute_hash({"b": 2, "a": 1})
        assert hash1 == hash2

    def test_compute_hash_returns_sha256(self) -> None:
        """_compute_hash should return SHA-256 hash (64 hex chars)."""
        hash_value = Snapshot._compute_hash({"test": "data"})
        assert len(hash_value) == 64
        assert all(c in "0123456789abcdef" for c in hash_value)

    def test_validate_hash_no_hash(self) -> None:
        """validate_hash should return True if no hash set."""
        snapshot = Snapshot(
            aggregate_id="agg-123",
            aggregate_type="User",
            version=5,
            state={"name": "John"},
            state_hash="",
        )
        assert snapshot.validate_hash() is True

    def test_validate_hash_valid(self) -> None:
        """validate_hash should return True for valid hash."""
        state = {"name": "John", "age": 30}
        valid_hash = Snapshot._compute_hash(state)
        snapshot = Snapshot(
            aggregate_id="agg-123",
            aggregate_type="User",
            version=5,
            state=state,
            state_hash=valid_hash,
        )
        assert snapshot.validate_hash() is True

    def test_validate_hash_invalid(self) -> None:
        """validate_hash should return False for invalid hash."""
        snapshot = Snapshot(
            aggregate_id="agg-123",
            aggregate_type="User",
            version=5,
            state={"name": "John"},
            state_hash="invalid_hash",
        )
        assert snapshot.validate_hash() is False

    def test_validate_hash_detects_tampering(self) -> None:
        """validate_hash should detect state tampering."""
        state = {"name": "John"}
        valid_hash = Snapshot._compute_hash(state)
        # Create snapshot with valid hash but different state
        snapshot = Snapshot(
            aggregate_id="agg-123",
            aggregate_type="User",
            version=5,
            state={"name": "Jane"},  # Tampered state
            state_hash=valid_hash,
        )
        assert snapshot.validate_hash() is False

    def test_compute_hash_handles_nested_dicts(self) -> None:
        """_compute_hash should handle nested dictionaries."""
        state = {"user": {"name": "John", "address": {"city": "NYC"}}}
        hash_value = Snapshot._compute_hash(state)
        assert len(hash_value) == 64

    def test_compute_hash_handles_lists(self) -> None:
        """_compute_hash should handle lists in state."""
        state = {"items": [1, 2, 3], "tags": ["a", "b"]}
        hash_value = Snapshot._compute_hash(state)
        assert len(hash_value) == 64

    def test_compute_hash_handles_datetime(self) -> None:
        """_compute_hash should handle datetime objects."""
        state = {"created": datetime.now(UTC)}
        hash_value = Snapshot._compute_hash(state)
        assert len(hash_value) == 64

    def test_compute_hash_empty_state(self) -> None:
        """_compute_hash should handle empty state."""
        hash_value = Snapshot._compute_hash({})
        assert len(hash_value) == 64
