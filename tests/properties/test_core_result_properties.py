"""Property-based tests for Result pattern.

Tests mathematical properties of the Result monad:
- Functor laws (map)
- Monad laws (bind/flatMap)
- Monoid laws (collect_results)
- Round-trip serialization

**Feature: core-improvements-2025**
**Validates: Result pattern correctness**
"""

import pytest
from hypothesis import given, strategies as st, assume, settings

from core.base.patterns.result import (
    Ok,
    Err,
    Result,
    ok,
    err,
    collect_results,
    result_from_dict,
)


# =============================================================================
# Strategies
# =============================================================================


@st.composite
def result_ok(draw, value_strategy=st.integers()):
    """Generate Ok results."""
    value = draw(value_strategy)
    return Ok(value)


@st.composite
def result_err(draw, error_strategy=st.text()):
    """Generate Err results."""
    error = draw(error_strategy)
    return Err(error)


@st.composite
def result_either(draw, value_strategy=st.integers(), error_strategy=st.text()):
    """Generate either Ok or Err results."""
    is_ok = draw(st.booleans())
    if is_ok:
        return draw(result_ok(value_strategy))
    else:
        return draw(result_err(error_strategy))


# =============================================================================
# Functor Laws for Result
# =============================================================================


class TestResultFunctorLaws:
    """Test that Result[T, E] is a valid Functor.

    Functor must satisfy:
    1. Identity: fmap id == id
    2. Composition: fmap (g . f) == fmap g . fmap f
    """

    @given(st.integers())
    @settings(max_examples=100)
    def test_functor_identity_ok(self, x: int) -> None:
        """Functor identity law: map(id) == id.

        **Feature: core-improvements-2025, Property 1: Functor Identity**
        **Validates: Result is a valid Functor**
        """
        result = Ok(x)
        identity = lambda y: y

        # map(id) should be the same as not mapping
        assert result.map(identity) == result

    @given(st.text())
    @settings(max_examples=100)
    def test_functor_identity_err(self, error: str) -> None:
        """Functor identity law for Err: map preserves Err."""
        result: Result[int, str] = Err(error)
        identity = lambda y: y

        assert result.map(identity) == result

    @given(st.integers())
    @settings(max_examples=100)
    def test_functor_composition_ok(self, x: int) -> None:
        """Functor composition law: map(g . f) == map(g) . map(f).

        **Feature: core-improvements-2025, Property 2: Functor Composition**
        **Validates: Result composition is associative**
        """
        result = Ok(x)
        f = lambda y: y + 1
        g = lambda y: y * 2

        # map(g . f) should equal map(g) after map(f)
        left = result.map(lambda y: g(f(y)))
        right = result.map(f).map(g)

        assert left == right

    @given(st.text())
    @settings(max_examples=100)
    def test_functor_composition_err(self, error: str) -> None:
        """Functor composition preserves Err."""
        result: Result[int, str] = Err(error)
        f = lambda y: y + 1
        g = lambda y: y * 2

        left = result.map(lambda y: g(f(y)))
        right = result.map(f).map(g)

        assert left == right


# =============================================================================
# Monad Laws for Result
# =============================================================================


class TestResultMonadLaws:
    """Test that Result[T, E] is a valid Monad.

    Monad must satisfy:
    1. Left identity: return a >>= f == f a
    2. Right identity: m >>= return == m
    3. Associativity: (m >>= f) >>= g == m >>= (\\x -> f x >>= g)
    """

    @given(st.integers())
    @settings(max_examples=100)
    def test_monad_left_identity(self, x: int) -> None:
        """Monad left identity: Ok(x).bind(f) == f(x).

        **Feature: core-improvements-2025, Property 3: Monad Left Identity**
        **Validates: Result bind behaves correctly**
        """
        f = lambda y: Ok(y * 2)

        # Ok(x).bind(f) should equal f(x)
        left = Ok(x).bind(f)
        right = f(x)

        assert left == right

    @given(st.integers())
    @settings(max_examples=100)
    def test_monad_right_identity(self, x: int) -> None:
        """Monad right identity: result.bind(Ok) == result.

        **Feature: core-improvements-2025, Property 4: Monad Right Identity**
        **Validates: Result bind with Ok is identity**
        """
        result = Ok(x)

        # result.bind(Ok) should equal result
        assert result.bind(Ok) == result

    @given(st.integers())
    @settings(max_examples=100)
    def test_monad_associativity_ok(self, x: int) -> None:
        """Monad associativity: (m >>= f) >>= g == m >>= (x -> f(x) >>= g).

        **Feature: core-improvements-2025, Property 5: Monad Associativity**
        **Validates: Result bind is associative**
        """
        result = Ok(x)
        f = lambda y: Ok(y + 1)
        g = lambda y: Ok(y * 2)

        # (result.bind(f)).bind(g)
        left = result.bind(f).bind(g)

        # result.bind(lambda x: f(x).bind(g))
        right = result.bind(lambda y: f(y).bind(g))

        assert left == right

    @given(st.text())
    @settings(max_examples=100)
    def test_monad_err_short_circuits(self, error: str) -> None:
        """Err short-circuits bind operations."""
        result: Result[int, str] = Err(error)
        f = lambda y: Ok(y * 2)

        # Err should propagate without calling f
        assert result.bind(f) == result


# =============================================================================
# Result-Specific Properties
# =============================================================================


class TestResultProperties:
    """Test Result-specific properties and invariants."""

    @given(st.integers())
    @settings(max_examples=100)
    def test_is_ok_is_err_mutual_exclusion(self, x: int) -> None:
        """Ok.is_ok() XOR Ok.is_err() must always be true.

        **Feature: core-improvements-2025, Property 6: Mutual Exclusion**
        **Validates: Result state is always consistent**
        """
        result = Ok(x)
        assert result.is_ok() != result.is_err()
        assert result.is_ok() and not result.is_err()

    @given(st.text())
    @settings(max_examples=100)
    def test_err_is_ok_is_err_mutual_exclusion(self, error: str) -> None:
        """Err.is_ok() XOR Err.is_err() must always be true."""
        result: Result[int, str] = Err(error)
        assert result.is_ok() != result.is_err()
        assert result.is_err() and not result.is_ok()

    @given(st.integers())
    @settings(max_examples=100)
    def test_unwrap_ok_returns_value(self, x: int) -> None:
        """Ok.unwrap() returns the wrapped value.

        **Feature: core-improvements-2025, Property 7: Unwrap Ok**
        **Validates: unwrap extracts value correctly**
        """
        result = Ok(x)
        assert result.unwrap() == x

    @given(st.text())
    @settings(max_examples=100)
    def test_unwrap_err_raises(self, error: str) -> None:
        """Err.unwrap() raises ValueError.

        **Feature: core-improvements-2025, Property 8: Unwrap Err Fails**
        **Validates: unwrap on Err is unsafe and raises**
        """
        result: Result[int, str] = Err(error)
        with pytest.raises(ValueError):
            result.unwrap()

    @given(st.integers(), st.integers())
    @settings(max_examples=100)
    def test_unwrap_or_ok_returns_value(self, x: int, default: int) -> None:
        """Ok.unwrap_or(default) returns value, ignoring default."""
        result = Ok(x)
        assert result.unwrap_or(default) == x

    @given(st.text(), st.integers())
    @settings(max_examples=100)
    def test_unwrap_or_err_returns_default(self, error: str, default: int) -> None:
        """Err.unwrap_or(default) returns default."""
        result: Result[int, str] = Err(error)
        assert result.unwrap_or(default) == default

    @given(st.integers())
    @settings(max_examples=100)
    def test_ok_equals_ok_with_same_value(self, x: int) -> None:
        """Ok(x) == Ok(x) for any x.

        **Feature: core-improvements-2025, Property 9: Value Equality**
        **Validates: Result implements value semantics**
        """
        assert Ok(x) == Ok(x)

    @given(st.integers(), st.integers())
    @settings(max_examples=100)
    def test_ok_not_equals_ok_with_different_value(self, x: int, y: int) -> None:
        """Ok(x) != Ok(y) if x != y."""
        assume(x != y)
        assert Ok(x) != Ok(y)

    @given(st.text())
    @settings(max_examples=100)
    def test_err_equals_err_with_same_error(self, error: str) -> None:
        """Err(e) == Err(e) for any e."""
        assert Err(error) == Err(error)


# =============================================================================
# Pattern Matching Properties
# =============================================================================


class TestResultPatternMatching:
    """Test pattern matching behavior."""

    @given(st.integers())
    @settings(max_examples=100)
    def test_match_ok_calls_on_ok(self, x: int) -> None:
        """match on Ok calls on_ok function.

        **Feature: core-improvements-2025, Property 10: Match Ok**
        **Validates: Pattern matching works correctly**
        """
        result = Ok(x)
        on_ok_called = False

        def on_ok(value: int) -> int:
            nonlocal on_ok_called
            on_ok_called = True
            return value * 2

        def on_err(error: str) -> int:
            return 0

        matched = result.match(on_ok, on_err)

        assert on_ok_called
        assert matched == x * 2

    @given(st.text())
    @settings(max_examples=100)
    def test_match_err_calls_on_err(self, error: str) -> None:
        """match on Err calls on_err function."""
        result: Result[int, str] = Err(error)
        on_err_called = False

        def on_ok(value: int) -> str:
            return "ok"

        def on_err(err: str) -> str:
            nonlocal on_err_called
            on_err_called = True
            return f"error: {err}"

        matched = result.match(on_ok, on_err)

        assert on_err_called
        assert matched == f"error: {error}"


# =============================================================================
# Collect Results Properties
# =============================================================================


class TestCollectResultsProperties:
    """Test collect_results aggregation properties.

    **Feature: core-improvements-2025, Property 15: Collect Results**
    **Validates: Aggregation behaves correctly**
    """

    @given(st.lists(st.integers(), min_size=1, max_size=10))
    @settings(max_examples=100)
    def test_collect_all_ok_returns_ok_list(self, values: list[int]) -> None:
        """collect_results with all Ok returns Ok with list of values."""
        results = [Ok(v) for v in values]
        collected = collect_results(results)

        assert collected.is_ok()
        assert collected.unwrap() == values

    @given(st.lists(st.integers(), min_size=1, max_size=10), st.text())
    @settings(max_examples=100)
    def test_collect_with_err_returns_first_err(
        self, values: list[int], error: str
    ) -> None:
        """collect_results returns first Err encountered."""
        results = [Ok(v) for v in values]
        # Insert Err at random position
        results.insert(len(results) // 2, Err(error))

        collected = collect_results(results)

        assert collected.is_err()
        assert collected.unwrap_err() == error

    def test_collect_empty_list_returns_ok_empty(self) -> None:
        """collect_results with empty list returns Ok([])."""
        results: list[Result[int, str]] = []
        collected = collect_results(results)

        assert collected.is_ok()
        assert collected.unwrap() == []


# =============================================================================
# Round-Trip Serialization Properties
# =============================================================================


class TestResultSerializationProperties:
    """Test round-trip serialization properties.

    **Feature: core-improvements-2025, Property 2: Result Round-Trip**
    **Validates: Serialization is lossless**
    """

    @given(st.integers())
    @settings(max_examples=100)
    def test_ok_round_trip_serialization(self, x: int) -> None:
        """Ok serialization round-trip preserves value."""
        original = Ok(x)
        serialized = original.to_dict()
        deserialized = result_from_dict(serialized)

        assert deserialized == original

    @given(st.text())
    @settings(max_examples=100)
    def test_err_round_trip_serialization(self, error: str) -> None:
        """Err serialization round-trip preserves error."""
        original: Result[int, str] = Err(error)
        serialized = original.to_dict()
        deserialized = result_from_dict(serialized)

        assert deserialized == original

    @given(st.integers())
    @settings(max_examples=100)
    def test_ok_to_dict_has_correct_structure(self, x: int) -> None:
        """Ok.to_dict() returns correct structure."""
        result = Ok(x)
        data = result.to_dict()

        assert data["type"] == "Ok"
        assert data["value"] == x
        assert "error" not in data

    @given(st.text())
    @settings(max_examples=100)
    def test_err_to_dict_has_correct_structure(self, error: str) -> None:
        """Err.to_dict() returns correct structure."""
        result: Result[int, str] = Err(error)
        data = result.to_dict()

        assert data["type"] == "Err"
        assert data["error"] == error
        assert "value" not in data


# =============================================================================
# Flatten Properties
# =============================================================================


class TestResultFlattenProperties:
    """Test flatten operation properties."""

    @given(st.integers())
    @settings(max_examples=100)
    def test_flatten_ok_ok_returns_inner_ok(self, x: int) -> None:
        """flatten(Ok(Ok(x))) == Ok(x).

        **Feature: core-improvements-2025, Property 11: Flatten Ok**
        **Validates: Flatten removes one level of nesting**
        """
        nested = Ok(Ok(x))
        flattened = nested.flatten()

        assert flattened == Ok(x)
        assert flattened.unwrap() == x

    @given(st.text())
    @settings(max_examples=100)
    def test_flatten_ok_err_returns_err(self, error: str) -> None:
        """flatten(Ok(Err(e))) == Err(e)."""
        nested: Result[Result[int, str], str] = Ok(Err(error))
        flattened = nested.flatten()

        assert flattened.is_err()
        assert flattened == Err(error)

    @given(st.text())
    @settings(max_examples=100)
    def test_flatten_err_returns_err(self, error: str) -> None:
        """flatten(Err(e)) == Err(e)."""
        result: Result[int, str] = Err(error)
        flattened = result.flatten()

        assert flattened == result


# =============================================================================
# Or Else Properties
# =============================================================================


class TestResultOrElseProperties:
    """Test or_else operation properties."""

    @given(st.integers(), st.text())
    @settings(max_examples=100)
    def test_ok_or_else_returns_ok(self, x: int, error: str) -> None:
        """Ok.or_else(f) returns Ok without calling f.

        **Feature: core-improvements-2025, Property 12: Or Else Ok**
        **Validates: or_else short-circuits on Ok**
        """
        result = Ok(x)
        called = False

        def recovery(e: str) -> Result[int, str]:
            nonlocal called
            called = True
            return Ok(0)

        recovered = result.or_else(recovery)

        assert not called
        assert recovered == result

    @given(st.text())
    @settings(max_examples=100)
    def test_err_or_else_calls_recovery(self, error: str) -> None:
        """Err.or_else(f) calls f with error.

        **Feature: core-improvements-2025, Property 13: Or Else Err**
        **Validates: or_else provides error recovery**
        """
        result: Result[int, str] = Err(error)
        called = False

        def recovery(e: str) -> Result[int, str]:
            nonlocal called
            called = True
            return Ok(42)

        recovered = result.or_else(recovery)

        assert called
        assert recovered == Ok(42)


# =============================================================================
# Inspect Properties
# =============================================================================


class TestResultInspectProperties:
    """Test inspect operations for side effects."""

    @given(st.integers())
    @settings(max_examples=100)
    def test_inspect_ok_calls_function_and_returns_self(self, x: int) -> None:
        """inspect on Ok calls function and returns self.

        **Feature: core-improvements-2025, Property 14: Inspect**
        **Validates: inspect allows side effects without changing result**
        """
        result = Ok(x)
        called = False
        captured = None

        def spy(value: int) -> None:
            nonlocal called, captured
            called = True
            captured = value

        inspected = result.inspect(spy)

        assert called
        assert captured == x
        assert inspected == result

    @given(st.text())
    @settings(max_examples=100)
    def test_inspect_err_does_not_call_function(self, error: str) -> None:
        """inspect on Err does not call function."""
        result: Result[int, str] = Err(error)
        called = False

        def spy(value: int) -> None:
            nonlocal called
            called = True

        inspected = result.inspect(spy)

        assert not called
        assert inspected == result

    @given(st.text())
    @settings(max_examples=100)
    def test_inspect_err_calls_function_and_returns_self(self, error: str) -> None:
        """inspect_err on Err calls function and returns self."""
        result: Result[int, str] = Err(error)
        called = False
        captured = None

        def spy(err: str) -> None:
            nonlocal called, captured
            called = True
            captured = err

        inspected = result.inspect_err(spy)

        assert called
        assert captured == error
        assert inspected == result
