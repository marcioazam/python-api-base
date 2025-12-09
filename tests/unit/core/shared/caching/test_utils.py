"""Unit tests for cache utilities.

**Feature: test-coverage-95-percent**
"""

import pytest

from core.shared.caching.utils import generate_cache_key


def sample_function(a: int, b: str) -> str:
    """Sample function for testing."""
    return f"{a}-{b}"


class NonStringable:
    """Class that raises on str()."""

    def __str__(self) -> str:
        raise ValueError("Cannot convert to string")


class TestGenerateCacheKey:
    """Tests for generate_cache_key function."""

    def test_generates_key_from_function(self) -> None:
        """Should generate key from function name."""
        key = generate_cache_key(sample_function, (), {})

        assert isinstance(key, str)
        assert len(key) == 32  # SHA-256 truncated to 32 chars

    def test_different_args_produce_different_keys(self) -> None:
        """Should produce different keys for different args."""
        key1 = generate_cache_key(sample_function, (1, "a"), {})
        key2 = generate_cache_key(sample_function, (2, "b"), {})

        assert key1 != key2

    def test_same_args_produce_same_key(self) -> None:
        """Should produce same key for same args."""
        key1 = generate_cache_key(sample_function, (1, "a"), {})
        key2 = generate_cache_key(sample_function, (1, "a"), {})

        assert key1 == key2

    def test_kwargs_affect_key(self) -> None:
        """Should include kwargs in key generation."""
        key1 = generate_cache_key(sample_function, (), {"x": 1})
        key2 = generate_cache_key(sample_function, (), {"x": 2})

        assert key1 != key2

    def test_kwargs_order_independent(self) -> None:
        """Should produce same key regardless of kwargs order."""
        key1 = generate_cache_key(sample_function, (), {"a": 1, "b": 2})
        key2 = generate_cache_key(sample_function, (), {"b": 2, "a": 1})

        assert key1 == key2

    def test_handles_non_stringable_args(self) -> None:
        """Should handle args that can't be converted to string."""
        obj = NonStringable()
        key = generate_cache_key(sample_function, (obj,), {})

        assert isinstance(key, str)
        assert len(key) == 32

    def test_handles_non_stringable_kwargs(self) -> None:
        """Should handle kwargs values that can't be converted to string."""
        obj = NonStringable()
        key = generate_cache_key(sample_function, (), {"obj": obj})

        assert isinstance(key, str)
        assert len(key) == 32

    def test_different_functions_produce_different_keys(self) -> None:
        """Should produce different keys for different functions."""
        def another_function() -> None:
            pass

        key1 = generate_cache_key(sample_function, (), {})
        key2 = generate_cache_key(another_function, (), {})

        assert key1 != key2
