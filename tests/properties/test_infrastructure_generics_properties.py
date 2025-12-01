"""Property-based tests for Infrastructure Generics.

**Feature: infrastructure-generics-review-2025**

This module contains property-based tests for:
- Result type operations (round-trip, map composition, error propagation)
- Status enum JSON serialization
- Error message formatting
- Protocol compliance verification
"""

import json
from typing import Any

import pytest
from hypothesis import given, strategies as st, settings, assume

from core.base.result import Ok, Err, Result, ok, err, try_catch
from infrastructure.generics.status import (
    BaseStatus,
    ConnectionStatus,
    TaskStatus,
    HealthStatus,
    CacheStatus,
    MessageStatus,
    AuthStatus,
)
from infrastructure.generics.errors import (
    ErrorMessages,
    InfrastructureError,
    AuthenticationError,
    CacheError,
    PoolError,
    ValidationError,
    SecurityError,
    MessagingError,
)


# =============================================================================
# Test Configuration
# =============================================================================

settings.register_profile("ci", max_examples=100)
settings.load_profile("ci")


# =============================================================================
# Strategies
# =============================================================================

# Simple value strategies for Result testing
simple_values = st.one_of(
    st.integers(),
    st.floats(allow_nan=False, allow_infinity=False),
    st.text(min_size=0, max_size=100),
    st.booleans(),
    st.none(),
)

# Non-None values for unwrap testing
non_none_values = st.one_of(
    st.integers(),
    st.floats(allow_nan=False, allow_infinity=False),
    st.text(min_size=1, max_size=100),
    st.booleans(),
)

# Error values
error_values = st.one_of(
    st.text(min_size=1, max_size=100),
    st.integers(),
)

# All status enums
all_status_enums = [
    BaseStatus,
    ConnectionStatus,
    TaskStatus,
    HealthStatus,
    CacheStatus,
    MessageStatus,
    AuthStatus,
]


# =============================================================================
# Property 1: Result Type Round-Trip
# **Feature: infrastructure-generics-review-2025, Property 1: Result Type Round-Trip**
# **Validates: Requirements 2.1, 2.3, 2.4**
# =============================================================================

class TestResultTypeRoundTrip:
    """Property tests for Result type round-trip behavior.
    
    *For any* value of type T, wrapping it in Ok and then unwrapping 
    should return the original value unchanged.
    """

    @given(value=simple_values)
    def test_ok_unwrap_returns_original_value(self, value: Any) -> None:
        """Ok(value).unwrap() == value for any value."""
        result = Ok(value)
        assert result.unwrap() == value

    @given(value=simple_values)
    def test_ok_unwrap_or_returns_value_not_default(self, value: Any) -> None:
        """Ok(value).unwrap_or(default) == value, ignoring default."""
        result = Ok(value)
        default = "default_sentinel"
        assert result.unwrap_or(default) == value

    @given(error=error_values, default=simple_values)
    def test_err_unwrap_or_returns_default(self, error: Any, default: Any) -> None:
        """Err(error).unwrap_or(default) == default."""
        result = Err(error)
        assert result.unwrap_or(default) == default

    @given(error=error_values)
    def test_err_unwrap_raises_error(self, error: Any) -> None:
        """Err(error).unwrap() raises ValueError."""
        result = Err(error)
        with pytest.raises(ValueError):
            result.unwrap()

    @given(value=simple_values)
    def test_ok_is_ok_true(self, value: Any) -> None:
        """Ok(value).is_ok() == True."""
        result = Ok(value)
        assert result.is_ok() is True
        assert result.is_err() is False

    @given(error=error_values)
    def test_err_is_err_true(self, error: Any) -> None:
        """Err(error).is_err() == True."""
        result = Err(error)
        assert result.is_err() is True
        assert result.is_ok() is False

    @given(value=simple_values)
    def test_ok_helper_creates_ok(self, value: Any) -> None:
        """ok(value) creates Ok(value)."""
        result = ok(value)
        assert isinstance(result, Ok)
        assert result.value == value

    @given(error=error_values)
    def test_err_helper_creates_err(self, error: Any) -> None:
        """err(error) creates Err(error)."""
        result = err(error)
        assert isinstance(result, Err)
        assert result.error == error


# =============================================================================
# Property 2: Result Map Composition
# **Feature: infrastructure-generics-review-2025, Property 2: Result Map Composition**
# **Validates: Requirements 2.4**
# =============================================================================

class TestResultMapComposition:
    """Property tests for Result map composition.
    
    *For any* Ok result and two functions f and g, 
    result.map(f).map(g) should equal result.map(lambda x: g(f(x))).
    """

    @given(value=st.integers(min_value=-1000, max_value=1000))
    def test_map_composition_integers(self, value: int) -> None:
        """map(f).map(g) == map(g ∘ f) for integer operations."""
        result = Ok(value)
        
        def f(x: int) -> int:
            return x + 1
        
        def g(x: int) -> int:
            return x * 2
        
        # Composition via chained maps
        chained = result.map(f).map(g)
        
        # Composition via single map
        composed = result.map(lambda x: g(f(x)))
        
        assert chained.unwrap() == composed.unwrap()

    @given(value=st.text(min_size=0, max_size=50))
    def test_map_composition_strings(self, value: str) -> None:
        """map(f).map(g) == map(g ∘ f) for string operations."""
        result = Ok(value)
        
        def f(x: str) -> str:
            return x.upper()
        
        def g(x: str) -> int:
            return len(x)
        
        chained = result.map(f).map(g)
        composed = result.map(lambda x: g(f(x)))
        
        assert chained.unwrap() == composed.unwrap()

    @given(value=st.integers())
    def test_map_identity(self, value: int) -> None:
        """map(identity) == identity for Ok results."""
        result = Ok(value)
        mapped = result.map(lambda x: x)
        assert mapped.unwrap() == result.unwrap()

    @given(value=st.integers())
    def test_bind_ok_chain(self, value: int) -> None:
        """bind chains Ok results correctly."""
        result = Ok(value)
        
        def add_one(x: int) -> Result[int, str]:
            return Ok(x + 1)
        
        def double(x: int) -> Result[int, str]:
            return Ok(x * 2)
        
        chained = result.bind(add_one).bind(double)
        expected = (value + 1) * 2
        
        assert chained.unwrap() == expected

    @given(value=st.integers())
    def test_bind_err_short_circuits(self, value: int) -> None:
        """bind short-circuits on Err."""
        result = Ok(value)
        
        def fail(x: int) -> Result[int, str]:
            return Err("error")
        
        def should_not_run(x: int) -> Result[int, str]:
            raise AssertionError("Should not be called")
        
        chained = result.bind(fail).bind(should_not_run)
        
        assert chained.is_err()
        assert chained.error == "error"


# =============================================================================
# Property 3: Result Error Propagation
# **Feature: infrastructure-generics-review-2025, Property 3: Result Error Propagation**
# **Validates: Requirements 2.2, 2.4**
# =============================================================================

class TestResultErrorPropagation:
    """Property tests for Result error propagation.
    
    *For any* Err result, calling map should return the same Err unchanged,
    preserving the error value.
    """

    @given(error=error_values)
    def test_err_map_preserves_error(self, error: Any) -> None:
        """Err.map(f) returns same Err unchanged."""
        result: Result[int, Any] = Err(error)
        
        def should_not_run(x: int) -> int:
            raise AssertionError("Should not be called")
        
        mapped = result.map(should_not_run)
        
        assert mapped.is_err()
        assert mapped.error == error

    @given(error=error_values)
    def test_err_bind_preserves_error(self, error: Any) -> None:
        """Err.bind(f) returns same Err unchanged."""
        result: Result[int, Any] = Err(error)
        
        def should_not_run(x: int) -> Result[int, Any]:
            raise AssertionError("Should not be called")
        
        mapped = result.bind(should_not_run)
        
        assert mapped.is_err()
        assert mapped.error == error

    @given(error=st.text(min_size=1, max_size=50))
    def test_map_err_transforms_error(self, error: str) -> None:
        """Err.map_err(f) transforms the error value."""
        result = Err(error)
        
        transformed = result.map_err(lambda e: f"wrapped: {e}")
        
        assert transformed.is_err()
        assert transformed.error == f"wrapped: {error}"

    @given(error=st.integers())
    def test_map_err_type_transformation(self, error: int) -> None:
        """map_err can change error type."""
        result = Err(error)
        
        transformed = result.map_err(str)
        
        assert transformed.is_err()
        assert transformed.error == str(error)
        assert isinstance(transformed.error, str)


# =============================================================================
# Property 18: Status Enum JSON Serialization
# **Feature: infrastructure-generics-review-2025, Property 18: Status Enum JSON Serialization**
# **Validates: Requirements 4.4**
# =============================================================================

class TestStatusEnumSerialization:
    """Property tests for status enum JSON serialization.
    
    *For any* status enum value, JSON serialization should produce 
    the string value of the enum.
    """

    @pytest.mark.parametrize("enum_class", all_status_enums)
    def test_enum_json_serialization(self, enum_class: type) -> None:
        """All enum values serialize to their string value."""
        for member in enum_class:
            # Serialize to JSON
            serialized = json.dumps(member)
            # Should be the quoted string value
            assert serialized == f'"{member.value}"'

    @pytest.mark.parametrize("enum_class", all_status_enums)
    def test_enum_json_round_trip(self, enum_class: type) -> None:
        """Enum values round-trip through JSON correctly."""
        for member in enum_class:
            # Serialize
            serialized = json.dumps(member)
            # Deserialize
            deserialized = json.loads(serialized)
            # Reconstruct enum
            reconstructed = enum_class(deserialized)
            assert reconstructed == member

    @pytest.mark.parametrize("enum_class", all_status_enums)
    def test_enum_str_mixin(self, enum_class: type) -> None:
        """All status enums use str mixin for string comparison."""
        assert issubclass(enum_class, str)
        for member in enum_class:
            # Enum inherits from str, so it's an instance of str
            assert isinstance(member, str)
            # The value is the string representation for comparison
            assert member.value == member.value.lower()
            # Can be compared directly with strings
            assert member == member.value

    @pytest.mark.parametrize("enum_class", all_status_enums)
    def test_enum_values_are_lowercase(self, enum_class: type) -> None:
        """All enum values are lowercase strings."""
        for member in enum_class:
            assert member.value == member.value.lower()
            assert member.value.isidentifier() or "_" in member.value

    def test_base_status_has_common_states(self) -> None:
        """BaseStatus has all common states."""
        expected = {"pending", "active", "completed", "failed", "cancelled"}
        actual = {s.value for s in BaseStatus}
        assert expected == actual

    def test_health_status_has_required_states(self) -> None:
        """HealthStatus has healthy, degraded, unhealthy."""
        expected = {"healthy", "degraded", "unhealthy"}
        actual = {s.value for s in HealthStatus}
        assert expected == actual


# =============================================================================
# Error Message Formatting Tests
# **Feature: infrastructure-generics-review-2025**
# **Validates: Requirements 3.1, 3.3, 3.4**
# =============================================================================

class TestErrorMessageFormatting:
    """Tests for centralized error message formatting."""

    @given(field=st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=("L",))))
    def test_validation_empty_value_formatting(self, field: str) -> None:
        """VALIDATION_EMPTY_VALUE formats correctly with field name."""
        message = ErrorMessages.format(
            ErrorMessages.VALIDATION_EMPTY_VALUE,
            field=field,
        )
        assert field in message
        assert "empty" in message.lower() or "whitespace" in message.lower()

    @given(
        field=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=("L",))),
        min_val=st.integers(min_value=0, max_value=100),
        max_val=st.integers(min_value=101, max_value=1000),
    )
    def test_validation_out_of_range_formatting(self, field: str, min_val: int, max_val: int) -> None:
        """VALIDATION_OUT_OF_RANGE formats correctly with field and range."""
        message = ErrorMessages.format(
            ErrorMessages.VALIDATION_OUT_OF_RANGE,
            field=field,
            min=str(min_val),
            max=str(max_val),
        )
        assert field in message
        assert str(min_val) in message
        assert str(max_val) in message

    @given(timeout=st.floats(min_value=0.1, max_value=300, allow_nan=False))
    def test_pool_acquire_timeout_formatting(self, timeout: float) -> None:
        """POOL_ACQUIRE_TIMEOUT formats correctly with timeout."""
        message = ErrorMessages.format(
            ErrorMessages.POOL_ACQUIRE_TIMEOUT,
            timeout=str(timeout),
        )
        assert str(timeout) in message
        assert "timeout" in message.lower()

    @given(
        expected=st.sampled_from(["RS256", "ES256", "HS256"]),
        received=st.sampled_from(["RS256", "ES256", "HS256", "none"]),
    )
    def test_auth_algorithm_mismatch_formatting(self, expected: str, received: str) -> None:
        """AUTH_ALGORITHM_MISMATCH formats correctly."""
        assume(expected != received)
        message = ErrorMessages.format(
            ErrorMessages.AUTH_ALGORITHM_MISMATCH,
            expected=expected,
            received=received,
        )
        assert expected in message
        assert received in message


# =============================================================================
# Error Class Hierarchy Tests
# **Feature: infrastructure-generics-review-2025**
# **Validates: Requirements 3.2**
# =============================================================================

class TestErrorClassHierarchy:
    """Tests for typed error class hierarchy."""

    def test_all_errors_inherit_from_infrastructure_error(self) -> None:
        """All error classes inherit from InfrastructureError."""
        error_classes = [
            AuthenticationError,
            CacheError,
            PoolError,
            ValidationError,
            SecurityError,
            MessagingError,
        ]
        for error_class in error_classes:
            assert issubclass(error_class, InfrastructureError)
            assert issubclass(error_class, Exception)

    @given(message=st.text(min_size=1, max_size=100))
    def test_infrastructure_error_has_message(self, message: str) -> None:
        """InfrastructureError stores message correctly."""
        error = InfrastructureError(message)
        assert error.message == message
        assert str(error) == f"[INFRASTRUCTURE_ERROR] {message}"

    @given(
        message=st.text(min_size=1, max_size=100),
        code=st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=("Lu",))),
    )
    def test_infrastructure_error_has_error_code(self, message: str, code: str) -> None:
        """InfrastructureError stores error_code correctly."""
        error = InfrastructureError(message, error_code=code)
        assert error.error_code == code
        assert f"[{code}]" in str(error)

    def test_validation_error_has_field(self) -> None:
        """ValidationError stores field name."""
        error = ValidationError("Invalid value", field="email")
        assert error.field == "email"

    @given(details=st.dictionaries(st.text(min_size=1, max_size=20), st.text(min_size=1, max_size=50), max_size=5))
    def test_infrastructure_error_has_details(self, details: dict) -> None:
        """InfrastructureError stores details dict."""
        error = InfrastructureError("Error", details=details)
        assert error.details == details


# =============================================================================
# try_catch Tests
# **Feature: infrastructure-generics-review-2025**
# **Validates: Requirements 2.5**
# =============================================================================

class TestTryCatch:
    """Tests for try_catch utility function."""

    @given(value=st.integers())
    def test_try_catch_success(self, value: int) -> None:
        """try_catch returns Ok on success."""
        def success_fn() -> int:
            return value
        
        result = try_catch(success_fn, ValueError)
        
        assert result.is_ok()
        assert result.unwrap() == value

    @given(error_msg=st.text(min_size=1, max_size=50))
    def test_try_catch_catches_error(self, error_msg: str) -> None:
        """try_catch returns Err on exception."""
        def failing_fn() -> int:
            raise ValueError(error_msg)
        
        result = try_catch(failing_fn, ValueError)
        
        assert result.is_err()
        assert error_msg in str(result.error)

    def test_try_catch_does_not_catch_other_errors(self) -> None:
        """try_catch only catches specified error type."""
        def failing_fn() -> int:
            raise TypeError("wrong type")
        
        with pytest.raises(TypeError):
            try_catch(failing_fn, ValueError)

    @given(value=st.integers())
    def test_try_catch_returns_exception_instance(self, value: int) -> None:
        """try_catch returns the exception instance in Err."""
        def failing_fn() -> int:
            raise ValueError(str(value))
        
        result = try_catch(failing_fn, ValueError)
        
        assert result.is_err()
        assert isinstance(result.error, ValueError)


# =============================================================================
# Property 4: Cache Type Preservation
# **Feature: infrastructure-generics-review-2025, Property 4: Cache Type Preservation**
# **Validates: Requirements 6.2, 6.3, 6.4**
# =============================================================================

def _create_cache():
    """Create a fresh in-memory cache."""
    from infrastructure.cache.providers import InMemoryCacheProvider
    from infrastructure.cache.config import CacheConfig
    return InMemoryCacheProvider[Any](CacheConfig(max_size=100, default_ttl=60))


class TestCacheTypePreservation:
    """Property tests for cache type preservation.
    
    *For any* cache provider and value of type T, storing and retrieving 
    the value should return an equivalent value of the same type.
    """

    @given(value=st.integers())
    @pytest.mark.asyncio
    async def test_integer_round_trip(self, value: int) -> None:
        """Integers are preserved through cache round-trip."""
        cache = _create_cache()
        await cache.set("test_key", value)
        retrieved = await cache.get("test_key")
        assert retrieved == value
        assert type(retrieved) == type(value)

    @given(value=st.text(min_size=0, max_size=100))
    @pytest.mark.asyncio
    async def test_string_round_trip(self, value: str) -> None:
        """Strings are preserved through cache round-trip."""
        cache = _create_cache()
        await cache.set("test_key", value)
        retrieved = await cache.get("test_key")
        assert retrieved == value

    @given(value=st.floats(allow_nan=False, allow_infinity=False))
    @pytest.mark.asyncio
    async def test_float_round_trip(self, value: float) -> None:
        """Floats are preserved through cache round-trip."""
        cache = _create_cache()
        await cache.set("test_key", value)
        retrieved = await cache.get("test_key")
        assert retrieved == value

    @given(value=st.booleans())
    @pytest.mark.asyncio
    async def test_boolean_round_trip(self, value: bool) -> None:
        """Booleans are preserved through cache round-trip."""
        cache = _create_cache()
        await cache.set("test_key", value)
        retrieved = await cache.get("test_key")
        assert retrieved == value
        assert type(retrieved) == type(value)

    @given(value=st.lists(st.integers(), min_size=0, max_size=20))
    @pytest.mark.asyncio
    async def test_list_round_trip(self, value: list) -> None:
        """Lists are preserved through cache round-trip."""
        cache = _create_cache()
        await cache.set("test_key", value)
        retrieved = await cache.get("test_key")
        assert retrieved == value

    @given(value=st.dictionaries(
        st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=("L",))),
        st.integers(),
        min_size=0,
        max_size=10
    ))
    @pytest.mark.asyncio
    async def test_dict_round_trip(self, value: dict) -> None:
        """Dictionaries are preserved through cache round-trip."""
        cache = _create_cache()
        await cache.set("test_key", value)
        retrieved = await cache.get("test_key")
        assert retrieved == value

    @pytest.mark.asyncio
    async def test_none_value_round_trip(self) -> None:
        """None values are preserved through cache round-trip."""
        cache = _create_cache()
        await cache.set("test_key", None)
        retrieved = await cache.get("test_key")
        assert retrieved is None

    @given(key=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("L", "N"))))
    @pytest.mark.asyncio
    async def test_missing_key_returns_none(self, key: str) -> None:
        """Missing keys return None."""
        cache = _create_cache()
        retrieved = await cache.get(key)
        assert retrieved is None


# =============================================================================
# Property 5: Cache Tag Invalidation
# **Feature: infrastructure-generics-review-2025, Property 5: Cache Tag Invalidation**
# **Validates: Requirements 6.5**
# =============================================================================

class TestCacheTagInvalidation:
    """Property tests for cache tag invalidation.
    
    *For any* cache with tagged entries, invalidating a tag should remove 
    all entries with that tag and only those entries.
    """

    @given(
        tag=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=("L",))),
        values=st.lists(st.integers(), min_size=1, max_size=10),
    )
    @pytest.mark.asyncio
    async def test_tag_invalidation_removes_all_tagged_entries(
        self, tag: str, values: list[int]
    ) -> None:
        """Invalidating a tag removes all entries with that tag."""
        cache = _create_cache()
        # Set multiple entries with the same tag
        for i, value in enumerate(values):
            await cache.set_with_tags(f"key_{i}", value, [tag])
        
        # Verify entries exist
        for i in range(len(values)):
            assert await cache.exists(f"key_{i}")
        
        # Invalidate by tag
        deleted_count = await cache.invalidate_by_tag(tag)
        
        # Verify all entries are removed
        assert deleted_count == len(values)
        for i in range(len(values)):
            assert not await cache.exists(f"key_{i}")

    @given(
        tag1=st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=("L",))),
        tag2=st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=("L",))),
    )
    @pytest.mark.asyncio
    async def test_tag_invalidation_preserves_other_tags(
        self, tag1: str, tag2: str
    ) -> None:
        """Invalidating one tag preserves entries with other tags."""
        assume(tag1 != tag2)
        cache = _create_cache()
        
        # Set entries with different tags
        await cache.set_with_tags("key_tag1", "value1", [tag1])
        await cache.set_with_tags("key_tag2", "value2", [tag2])
        
        # Invalidate tag1
        await cache.invalidate_by_tag(tag1)
        
        # tag1 entry should be gone
        assert not await cache.exists("key_tag1")
        # tag2 entry should remain
        assert await cache.exists("key_tag2")
        assert await cache.get("key_tag2") == "value2"

    @given(
        tags=st.lists(
            st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=("L",))),
            min_size=2,
            max_size=5,
            unique=True,
        )
    )
    @pytest.mark.asyncio
    async def test_entry_with_multiple_tags(self, tags: list[str]) -> None:
        """Entry with multiple tags is removed when any tag is invalidated."""
        cache = _create_cache()
        await cache.set_with_tags("multi_tag_key", "value", tags)
        
        # Verify entry exists
        assert await cache.exists("multi_tag_key")
        
        # Invalidate first tag
        await cache.invalidate_by_tag(tags[0])
        
        # Entry should be removed
        assert not await cache.exists("multi_tag_key")

    @pytest.mark.asyncio
    async def test_invalidate_nonexistent_tag(self) -> None:
        """Invalidating a nonexistent tag returns 0 and doesn't error."""
        cache = _create_cache()
        deleted_count = await cache.invalidate_by_tag("nonexistent_tag")
        assert deleted_count == 0

    @given(value=st.integers())
    @pytest.mark.asyncio
    async def test_untagged_entries_not_affected(self, value: int) -> None:
        """Untagged entries are not affected by tag invalidation."""
        cache = _create_cache()
        # Set an untagged entry
        await cache.set("untagged_key", value)
        # Set a tagged entry
        await cache.set_with_tags("tagged_key", value + 1, ["some_tag"])
        
        # Invalidate the tag
        await cache.invalidate_by_tag("some_tag")
        
        # Untagged entry should remain
        assert await cache.exists("untagged_key")
        assert await cache.get("untagged_key") == value


# =============================================================================
# Property 6: Pool Counter Invariant
# **Feature: infrastructure-generics-review-2025, Property 6: Pool Counter Invariant**
# **Validates: Requirements 5.5**
# =============================================================================

class TestPoolCounterInvariant:
    """Property tests for pool counter invariant.
    
    *For any* connection pool state, the sum of idle, in_use, and unhealthy 
    connections should equal the total connections.
    """

    @pytest.mark.asyncio
    async def test_initial_pool_invariant(self) -> None:
        """Pool invariant holds after initialization."""
        from infrastructure.connection_pool.service import ConnectionPool
        from infrastructure.connection_pool.config import PoolConfig
        from infrastructure.connection_pool.factory import ConnectionFactory
        
        class MockConnection:
            pass
        
        class MockFactory(ConnectionFactory[MockConnection]):
            async def create(self) -> MockConnection:
                return MockConnection()
            
            async def destroy(self, connection: MockConnection) -> None:
                pass
            
            async def validate(self, connection: MockConnection) -> bool:
                return True
        
        config = PoolConfig(min_size=3, max_size=10)
        pool = ConnectionPool[MockConnection](MockFactory(), config)
        await pool.initialize()
        
        try:
            stats = pool.get_stats()
            total = stats.idle_connections + stats.in_use_connections + stats.unhealthy_connections
            assert total == stats.total_connections
        finally:
            await pool.close()

    @pytest.mark.asyncio
    async def test_pool_invariant_after_acquire(self) -> None:
        """Pool invariant holds after acquiring connections."""
        from infrastructure.connection_pool.service import ConnectionPool
        from infrastructure.connection_pool.config import PoolConfig
        from infrastructure.connection_pool.factory import ConnectionFactory
        
        class MockConnection:
            pass
        
        class MockFactory(ConnectionFactory[MockConnection]):
            async def create(self) -> MockConnection:
                return MockConnection()
            
            async def destroy(self, connection: MockConnection) -> None:
                pass
            
            async def validate(self, connection: MockConnection) -> bool:
                return True
        
        config = PoolConfig(min_size=3, max_size=10)
        pool = ConnectionPool[MockConnection](MockFactory(), config)
        await pool.initialize()
        
        try:
            # Acquire some connections
            conn1, id1 = await pool.acquire()
            conn2, id2 = await pool.acquire()
            
            stats = pool.get_stats()
            total = stats.idle_connections + stats.in_use_connections + stats.unhealthy_connections
            assert total == stats.total_connections
            assert stats.in_use_connections == 2
            
            # Release one
            await pool.release(id1)
            
            stats = pool.get_stats()
            total = stats.idle_connections + stats.in_use_connections + stats.unhealthy_connections
            assert total == stats.total_connections
            assert stats.in_use_connections == 1
            
            await pool.release(id2)
        finally:
            await pool.close()

    @given(num_acquires=st.integers(min_value=1, max_value=5))
    @pytest.mark.asyncio
    async def test_pool_invariant_multiple_operations(self, num_acquires: int) -> None:
        """Pool invariant holds after multiple acquire/release operations."""
        from infrastructure.connection_pool.service import ConnectionPool
        from infrastructure.connection_pool.config import PoolConfig
        from infrastructure.connection_pool.factory import ConnectionFactory
        
        class MockConnection:
            pass
        
        class MockFactory(ConnectionFactory[MockConnection]):
            async def create(self) -> MockConnection:
                return MockConnection()
            
            async def destroy(self, connection: MockConnection) -> None:
                pass
            
            async def validate(self, connection: MockConnection) -> bool:
                return True
        
        config = PoolConfig(min_size=2, max_size=10)
        pool = ConnectionPool[MockConnection](MockFactory(), config)
        await pool.initialize()
        
        try:
            acquired = []
            
            # Acquire connections
            for _ in range(num_acquires):
                conn, conn_id = await pool.acquire()
                acquired.append(conn_id)
                
                # Check invariant after each acquire
                stats = pool.get_stats()
                total = stats.idle_connections + stats.in_use_connections + stats.unhealthy_connections
                assert total == stats.total_connections
            
            # Release all
            for conn_id in acquired:
                await pool.release(conn_id)
                
                # Check invariant after each release
                stats = pool.get_stats()
                total = stats.idle_connections + stats.in_use_connections + stats.unhealthy_connections
                assert total == stats.total_connections
        finally:
            await pool.close()


# =============================================================================
# Property 7: Pool Acquire-Release Round-Trip
# **Feature: infrastructure-generics-review-2025, Property 7: Pool Acquire-Release Round-Trip**
# **Validates: Requirements 5.3, 5.4**
# =============================================================================

class TestPoolAcquireReleaseRoundTrip:
    """Property tests for pool acquire-release round-trip.
    
    *For any* connection pool, acquiring and then releasing a connection 
    should return the pool to a valid state with the same total connections.
    """

    @pytest.mark.asyncio
    async def test_acquire_release_preserves_total(self) -> None:
        """Acquire-release preserves total connection count."""
        from infrastructure.connection_pool.service import ConnectionPool
        from infrastructure.connection_pool.config import PoolConfig
        from infrastructure.connection_pool.factory import ConnectionFactory
        
        class MockConnection:
            pass
        
        class MockFactory(ConnectionFactory[MockConnection]):
            async def create(self) -> MockConnection:
                return MockConnection()
            
            async def destroy(self, connection: MockConnection) -> None:
                pass
            
            async def validate(self, connection: MockConnection) -> bool:
                return True
        
        config = PoolConfig(min_size=3, max_size=10)
        pool = ConnectionPool[MockConnection](MockFactory(), config)
        await pool.initialize()
        
        try:
            initial_stats = pool.get_stats()
            initial_total = initial_stats.total_connections
            
            # Acquire and release
            conn, conn_id = await pool.acquire()
            await pool.release(conn_id)
            
            final_stats = pool.get_stats()
            assert final_stats.total_connections == initial_total
        finally:
            await pool.close()

    @pytest.mark.asyncio
    async def test_acquire_release_returns_to_idle(self) -> None:
        """Released connection returns to idle state."""
        from infrastructure.connection_pool.service import ConnectionPool
        from infrastructure.connection_pool.config import PoolConfig
        from infrastructure.connection_pool.factory import ConnectionFactory
        
        class MockConnection:
            pass
        
        class MockFactory(ConnectionFactory[MockConnection]):
            async def create(self) -> MockConnection:
                return MockConnection()
            
            async def destroy(self, connection: MockConnection) -> None:
                pass
            
            async def validate(self, connection: MockConnection) -> bool:
                return True
        
        config = PoolConfig(min_size=3, max_size=10)
        pool = ConnectionPool[MockConnection](MockFactory(), config)
        await pool.initialize()
        
        try:
            initial_idle = pool.get_stats().idle_connections
            
            # Acquire
            conn, conn_id = await pool.acquire()
            assert pool.get_stats().idle_connections == initial_idle - 1
            
            # Release
            await pool.release(conn_id)
            assert pool.get_stats().idle_connections == initial_idle
        finally:
            await pool.close()

    @pytest.mark.asyncio
    async def test_context_manager_round_trip(self) -> None:
        """Context manager properly acquires and releases."""
        from infrastructure.connection_pool.service import ConnectionPool, ConnectionPoolContext
        from infrastructure.connection_pool.config import PoolConfig
        from infrastructure.connection_pool.factory import ConnectionFactory
        
        class MockConnection:
            pass
        
        class MockFactory(ConnectionFactory[MockConnection]):
            async def create(self) -> MockConnection:
                return MockConnection()
            
            async def destroy(self, connection: MockConnection) -> None:
                pass
            
            async def validate(self, connection: MockConnection) -> bool:
                return True
        
        config = PoolConfig(min_size=3, max_size=10)
        pool = ConnectionPool[MockConnection](MockFactory(), config)
        await pool.initialize()
        
        try:
            initial_idle = pool.get_stats().idle_connections
            
            async with ConnectionPoolContext(pool) as conn:
                assert pool.get_stats().idle_connections == initial_idle - 1
                assert conn is not None
            
            # After context exit, connection should be released
            assert pool.get_stats().idle_connections == initial_idle
        finally:
            await pool.close()

    @given(num_cycles=st.integers(min_value=1, max_value=10))
    @pytest.mark.asyncio
    async def test_multiple_acquire_release_cycles(self, num_cycles: int) -> None:
        """Multiple acquire-release cycles maintain pool integrity."""
        from infrastructure.connection_pool.service import ConnectionPool
        from infrastructure.connection_pool.config import PoolConfig
        from infrastructure.connection_pool.factory import ConnectionFactory
        
        class MockConnection:
            pass
        
        class MockFactory(ConnectionFactory[MockConnection]):
            async def create(self) -> MockConnection:
                return MockConnection()
            
            async def destroy(self, connection: MockConnection) -> None:
                pass
            
            async def validate(self, connection: MockConnection) -> bool:
                return True
        
        config = PoolConfig(min_size=2, max_size=10)
        pool = ConnectionPool[MockConnection](MockFactory(), config)
        await pool.initialize()
        
        try:
            initial_total = pool.get_stats().total_connections
            
            for _ in range(num_cycles):
                conn, conn_id = await pool.acquire()
                await pool.release(conn_id)
            
            final_stats = pool.get_stats()
            assert final_stats.total_connections == initial_total
            # All connections should be idle after all releases
            assert final_stats.in_use_connections == 0
        finally:
            await pool.close()


# =============================================================================
# Property 8: Token Store Immutability
# **Feature: infrastructure-generics-review-2025, Property 8: Token Store Immutability**
# **Validates: Requirements 8.2**
# =============================================================================

class TestTokenStoreImmutability:
    """Property tests for token store immutability.
    
    *For any* StoredToken instance, attempting to modify any field 
    should raise an error (frozen dataclass).
    """

    @settings(deadline=None)
    @given(
        jti=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("L", "N"))),
        user_id=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("L", "N"))),
    )
    def test_stored_token_is_frozen(self, jti: str, user_id: str) -> None:
        """StoredToken fields cannot be modified after creation."""
        from infrastructure.auth.token_store.models import StoredToken
        from datetime import datetime, UTC, timedelta
        
        token = StoredToken(
            jti=jti,
            user_id=user_id,
            created_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            revoked=False,
        )
        
        # Attempting to modify any field should raise FrozenInstanceError
        with pytest.raises(Exception):  # dataclasses.FrozenInstanceError
            token.jti = "new_jti"
        
        with pytest.raises(Exception):
            token.user_id = "new_user"
        
        with pytest.raises(Exception):
            token.revoked = True

    @given(
        jti=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("L", "N"))),
        user_id=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("L", "N"))),
    )
    def test_stored_token_uses_slots(self, jti: str, user_id: str) -> None:
        """StoredToken uses __slots__ for memory efficiency."""
        from infrastructure.auth.token_store.models import StoredToken
        from datetime import datetime, UTC, timedelta
        
        token = StoredToken(
            jti=jti,
            user_id=user_id,
            created_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        
        # Slots-based classes don't have __dict__
        assert not hasattr(token, "__dict__")


# =============================================================================
# Property 9: Token Store Input Validation
# **Feature: infrastructure-generics-review-2025, Property 9: Token Store Input Validation**
# **Validates: Requirements 8.3**
# =============================================================================

class TestTokenStoreInputValidation:
    """Property tests for token store input validation.
    
    *For any* string composed entirely of whitespace, storing it as a 
    token identifier should be rejected with a validation error.
    """

    @given(whitespace=st.text(alphabet=" \t\n\r", min_size=0, max_size=20))
    @pytest.mark.asyncio
    async def test_empty_jti_rejected(self, whitespace: str) -> None:
        """Empty or whitespace-only jti is rejected."""
        from infrastructure.auth.token_store.stores import InMemoryTokenStore
        from datetime import datetime, UTC, timedelta
        
        store = InMemoryTokenStore()
        
        with pytest.raises(ValueError, match="jti cannot be empty"):
            await store.store(
                jti=whitespace,
                user_id="valid_user",
                expires_at=datetime.now(UTC) + timedelta(hours=1),
            )

    @given(whitespace=st.text(alphabet=" \t\n\r", min_size=0, max_size=20))
    @pytest.mark.asyncio
    async def test_empty_user_id_rejected(self, whitespace: str) -> None:
        """Empty or whitespace-only user_id is rejected."""
        from infrastructure.auth.token_store.stores import InMemoryTokenStore
        from datetime import datetime, UTC, timedelta
        
        store = InMemoryTokenStore()
        
        with pytest.raises(ValueError, match="user_id cannot be empty"):
            await store.store(
                jti="valid_jti",
                user_id=whitespace,
                expires_at=datetime.now(UTC) + timedelta(hours=1),
            )

    @pytest.mark.asyncio
    async def test_naive_datetime_rejected(self) -> None:
        """Naive datetime (without timezone) is rejected."""
        from infrastructure.auth.token_store.stores import InMemoryTokenStore
        from datetime import datetime, timedelta
        
        store = InMemoryTokenStore()
        
        with pytest.raises(ValueError, match="timezone-aware"):
            await store.store(
                jti="valid_jti",
                user_id="valid_user",
                expires_at=datetime.now() + timedelta(hours=1),  # Naive datetime
            )

    @given(
        jti=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("L", "N"))),
        user_id=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("L", "N"))),
    )
    @pytest.mark.asyncio
    async def test_valid_input_accepted(self, jti: str, user_id: str) -> None:
        """Valid input is accepted without error."""
        from infrastructure.auth.token_store.stores import InMemoryTokenStore
        from datetime import datetime, UTC, timedelta
        
        store = InMemoryTokenStore()
        
        # Should not raise
        await store.store(
            jti=jti,
            user_id=user_id,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        
        # Verify token was stored
        token = await store.get(jti)
        assert token is not None
        assert token.jti == jti
        assert token.user_id == user_id


# =============================================================================
# Property 10: Token Revocation Atomicity
# **Feature: infrastructure-generics-review-2025, Property 10: Token Revocation Atomicity**
# **Validates: Requirements 8.5**
# =============================================================================

class TestTokenRevocationAtomicity:
    """Property tests for token revocation atomicity.
    
    *For any* token store and token, after revocation the token should 
    be marked as revoked in all subsequent queries.
    """

    @given(
        jti=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("L", "N"))),
        user_id=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("L", "N"))),
    )
    @pytest.mark.asyncio
    async def test_revoked_token_stays_revoked(self, jti: str, user_id: str) -> None:
        """Once revoked, token remains revoked in all queries."""
        from infrastructure.auth.token_store.stores import InMemoryTokenStore
        from datetime import datetime, UTC, timedelta
        
        store = InMemoryTokenStore()
        
        # Store token
        await store.store(
            jti=jti,
            user_id=user_id,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        
        # Verify token is valid before revocation
        assert await store.is_valid(jti)
        
        # Revoke token
        result = await store.revoke(jti)
        assert result is True
        
        # Verify token is no longer valid
        assert not await store.is_valid(jti)
        
        # Verify token is marked as revoked
        token = await store.get(jti)
        assert token is not None
        assert token.revoked is True

    @given(
        user_id=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("L", "N"))),
        num_tokens=st.integers(min_value=1, max_value=5),
    )
    @pytest.mark.asyncio
    async def test_revoke_all_for_user(self, user_id: str, num_tokens: int) -> None:
        """Revoking all tokens for a user revokes all of them."""
        from infrastructure.auth.token_store.stores import InMemoryTokenStore
        from datetime import datetime, UTC, timedelta
        
        store = InMemoryTokenStore()
        jtis = []
        
        # Store multiple tokens for the same user
        for i in range(num_tokens):
            jti = f"token_{user_id}_{i}"
            jtis.append(jti)
            await store.store(
                jti=jti,
                user_id=user_id,
                expires_at=datetime.now(UTC) + timedelta(hours=1),
            )
        
        # Verify all tokens are valid
        for jti in jtis:
            assert await store.is_valid(jti)
        
        # Revoke all tokens for user
        revoked_count = await store.revoke_all_for_user(user_id)
        assert revoked_count == num_tokens
        
        # Verify all tokens are now invalid
        for jti in jtis:
            assert not await store.is_valid(jti)
            token = await store.get(jti)
            assert token.revoked is True

    @pytest.mark.asyncio
    async def test_revoke_nonexistent_token(self) -> None:
        """Revoking a nonexistent token returns False."""
        from infrastructure.auth.token_store.stores import InMemoryTokenStore
        
        store = InMemoryTokenStore()
        
        result = await store.revoke("nonexistent_jti")
        assert result is False

    @given(
        jti=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("L", "N"))),
        user_id=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("L", "N"))),
    )
    @pytest.mark.asyncio
    async def test_double_revocation_is_idempotent(self, jti: str, user_id: str) -> None:
        """Revoking an already revoked token is idempotent."""
        from infrastructure.auth.token_store.stores import InMemoryTokenStore
        from datetime import datetime, UTC, timedelta
        
        store = InMemoryTokenStore()
        
        # Store token
        await store.store(
            jti=jti,
            user_id=user_id,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        
        # First revocation
        result1 = await store.revoke(jti)
        assert result1 is True
        
        # Second revocation (should still succeed)
        result2 = await store.revoke(jti)
        assert result2 is True
        
        # Token should still be revoked
        assert not await store.is_valid(jti)


# =============================================================================
# Property 11: Compression Round-Trip
# **Feature: infrastructure-generics-review-2025, Property 11: Compression Round-Trip**
# **Validates: Requirements 9.1, 9.4**
# =============================================================================

class TestCompressionRoundTrip:
    """Property tests for compression round-trip.
    
    *For any* compressor and byte sequence, compressing and then 
    decompressing should return the original bytes.
    """

    @given(data=st.binary(min_size=0, max_size=10000))
    def test_gzip_round_trip(self, data: bytes) -> None:
        """GZip compression round-trip preserves data."""
        from infrastructure.compression.compressors import GzipCompressor
        
        compressor = GzipCompressor(level=6)
        compressed = compressor.compress(data)
        decompressed = compressor.decompress(compressed)
        
        assert decompressed == data

    @given(data=st.binary(min_size=0, max_size=10000))
    def test_deflate_round_trip(self, data: bytes) -> None:
        """Deflate compression round-trip preserves data."""
        from infrastructure.compression.compressors import DeflateCompressor
        
        compressor = DeflateCompressor(level=6)
        compressed = compressor.compress(data)
        decompressed = compressor.decompress(compressed)
        
        assert decompressed == data

    @given(data=st.binary(min_size=0, max_size=10000))
    def test_identity_round_trip(self, data: bytes) -> None:
        """Identity compression round-trip preserves data."""
        from infrastructure.compression.compressors import IdentityCompressor
        
        compressor = IdentityCompressor()
        compressed = compressor.compress(data)
        decompressed = compressor.decompress(compressed)
        
        assert decompressed == data
        assert compressed == data  # Identity should not modify data

    @given(
        data=st.binary(min_size=1, max_size=5000),
        level=st.integers(min_value=1, max_value=9),
    )
    def test_gzip_different_levels_round_trip(self, data: bytes, level: int) -> None:
        """GZip compression at different levels preserves data."""
        from infrastructure.compression.compressors import GzipCompressor
        
        compressor = GzipCompressor(level=level)
        compressed = compressor.compress(data)
        decompressed = compressor.decompress(compressed)
        
        assert decompressed == data

    @given(
        data=st.binary(min_size=1, max_size=5000),
        level=st.integers(min_value=1, max_value=9),
    )
    def test_deflate_different_levels_round_trip(self, data: bytes, level: int) -> None:
        """Deflate compression at different levels preserves data."""
        from infrastructure.compression.compressors import DeflateCompressor
        
        compressor = DeflateCompressor(level=level)
        compressed = compressor.compress(data)
        decompressed = compressor.decompress(compressed)
        
        assert decompressed == data


# =============================================================================
# Property 12: Compression Algorithm Selection
# **Feature: infrastructure-generics-review-2025, Property 12: Compression Algorithm Selection**
# **Validates: Requirements 9.3**
# =============================================================================

class TestCompressionAlgorithmSelection:
    """Property tests for compression algorithm selection.
    
    *For any* Accept-Encoding header and supported algorithms, the selected 
    algorithm should be the highest-priority supported algorithm from the header.
    """

    def test_gzip_selected_when_supported(self) -> None:
        """GZip is selected when in Accept-Encoding and supported."""
        from infrastructure.compression.factory import select_best_algorithm
        from infrastructure.compression.enums import CompressionAlgorithm
        
        supported = (CompressionAlgorithm.GZIP, CompressionAlgorithm.DEFLATE, CompressionAlgorithm.IDENTITY)
        result = select_best_algorithm("gzip, deflate", supported)
        
        assert result == CompressionAlgorithm.GZIP

    def test_deflate_selected_when_gzip_not_supported(self) -> None:
        """Deflate is selected when gzip not supported."""
        from infrastructure.compression.factory import select_best_algorithm
        from infrastructure.compression.enums import CompressionAlgorithm
        
        supported = (CompressionAlgorithm.DEFLATE, CompressionAlgorithm.IDENTITY)
        result = select_best_algorithm("gzip, deflate", supported)
        
        assert result == CompressionAlgorithm.DEFLATE

    def test_identity_when_no_match(self) -> None:
        """Identity is returned when no algorithms match."""
        from infrastructure.compression.factory import select_best_algorithm
        from infrastructure.compression.enums import CompressionAlgorithm
        
        supported = (CompressionAlgorithm.IDENTITY,)
        result = select_best_algorithm("gzip, deflate", supported)
        
        assert result == CompressionAlgorithm.IDENTITY

    def test_quality_value_ordering(self) -> None:
        """Higher quality values are preferred."""
        from infrastructure.compression.factory import select_best_algorithm
        from infrastructure.compression.enums import CompressionAlgorithm
        
        supported = (CompressionAlgorithm.GZIP, CompressionAlgorithm.DEFLATE, CompressionAlgorithm.IDENTITY)
        # deflate has higher quality than gzip
        result = select_best_algorithm("gzip;q=0.5, deflate;q=0.9", supported)
        
        assert result == CompressionAlgorithm.DEFLATE

    def test_zero_quality_excluded(self) -> None:
        """Algorithms with q=0 are excluded."""
        from infrastructure.compression.factory import select_best_algorithm
        from infrastructure.compression.enums import CompressionAlgorithm
        
        supported = (CompressionAlgorithm.GZIP, CompressionAlgorithm.DEFLATE, CompressionAlgorithm.IDENTITY)
        result = select_best_algorithm("gzip;q=0, deflate", supported)
        
        assert result == CompressionAlgorithm.DEFLATE

    def test_empty_header_returns_identity(self) -> None:
        """Empty Accept-Encoding returns identity."""
        from infrastructure.compression.factory import select_best_algorithm
        from infrastructure.compression.enums import CompressionAlgorithm
        
        supported = (CompressionAlgorithm.GZIP, CompressionAlgorithm.DEFLATE, CompressionAlgorithm.IDENTITY)
        result = select_best_algorithm("", supported)
        
        assert result == CompressionAlgorithm.IDENTITY

    @given(
        encodings=st.lists(
            st.sampled_from(["gzip", "deflate", "identity"]),
            min_size=1,
            max_size=3,
            unique=True,
        )
    )
    def test_first_supported_algorithm_selected(self, encodings: list[str]) -> None:
        """First supported algorithm in header is selected."""
        from infrastructure.compression.factory import select_best_algorithm, parse_accept_encoding
        from infrastructure.compression.enums import CompressionAlgorithm
        
        header = ", ".join(encodings)
        supported = (CompressionAlgorithm.GZIP, CompressionAlgorithm.DEFLATE, CompressionAlgorithm.IDENTITY)
        
        result = select_best_algorithm(header, supported)
        
        # Result should be one of the requested encodings
        encoding_map = {
            "gzip": CompressionAlgorithm.GZIP,
            "deflate": CompressionAlgorithm.DEFLATE,
            "identity": CompressionAlgorithm.IDENTITY,
        }
        expected_algorithms = [encoding_map[e] for e in encodings]
        assert result in expected_algorithms

    def test_parse_accept_encoding_with_quality(self) -> None:
        """Parse Accept-Encoding correctly extracts quality values."""
        from infrastructure.compression.factory import parse_accept_encoding
        from infrastructure.compression.enums import CompressionAlgorithm
        
        result = parse_accept_encoding("gzip;q=0.8, deflate;q=0.6, identity;q=0.1")
        
        # Should be sorted by quality descending
        assert len(result) == 3
        assert result[0] == (CompressionAlgorithm.GZIP, 0.8)
        assert result[1] == (CompressionAlgorithm.DEFLATE, 0.6)
        assert result[2] == (CompressionAlgorithm.IDENTITY, 0.1)



# =============================================================================
# Property 13: Event Bus Type Safety
# **Feature: infrastructure-generics-review-2025, Property 13: Event Bus Type Safety**
# **Validates: Requirements 10.3**
# =============================================================================

class TestEventBusTypeSafety:
    """Property tests for event bus type safety.
    
    *For any* event bus subscription, handlers should only receive 
    events of the subscribed type.
    """

    @pytest.mark.asyncio
    async def test_handler_receives_correct_event_type(self) -> None:
        """Handler receives only events of subscribed type."""
        from infrastructure.messaging.generics import EventBus, EventHandler
        from dataclasses import dataclass
        
        @dataclass
        class UserCreatedEvent:
            user_id: str
        
        @dataclass
        class OrderCreatedEvent:
            order_id: str
        
        received_events: list[UserCreatedEvent] = []
        
        class UserEventHandler:
            async def handle(self, event: UserCreatedEvent) -> None:
                received_events.append(event)
        
        bus: EventBus[UserCreatedEvent | OrderCreatedEvent] = EventBus()
        handler = UserEventHandler()
        bus.subscribe(UserCreatedEvent, handler)
        
        # Publish user event - should be received
        user_event = UserCreatedEvent(user_id="user-1")
        await bus.publish(user_event)
        
        assert len(received_events) == 1
        assert received_events[0] == user_event

    @pytest.mark.asyncio
    async def test_handler_does_not_receive_other_event_types(self) -> None:
        """Handler does not receive events of other types."""
        from infrastructure.messaging.generics import EventBus
        from dataclasses import dataclass
        
        @dataclass
        class UserCreatedEvent:
            user_id: str
        
        @dataclass
        class OrderCreatedEvent:
            order_id: str
        
        user_events: list[UserCreatedEvent] = []
        order_events: list[OrderCreatedEvent] = []
        
        class UserEventHandler:
            async def handle(self, event: UserCreatedEvent) -> None:
                user_events.append(event)
        
        class OrderEventHandler:
            async def handle(self, event: OrderCreatedEvent) -> None:
                order_events.append(event)
        
        bus: EventBus[UserCreatedEvent | OrderCreatedEvent] = EventBus()
        bus.subscribe(UserCreatedEvent, UserEventHandler())
        bus.subscribe(OrderCreatedEvent, OrderEventHandler())
        
        # Publish order event
        order_event = OrderCreatedEvent(order_id="order-1")
        await bus.publish(order_event)
        
        # User handler should not receive order event
        assert len(user_events) == 0
        assert len(order_events) == 1

    @given(num_events=st.integers(min_value=1, max_value=10))
    @pytest.mark.asyncio
    async def test_multiple_events_received_in_order(self, num_events: int) -> None:
        """Multiple events are received by handler."""
        from infrastructure.messaging.generics import EventBus
        from dataclasses import dataclass
        
        @dataclass
        class TestEvent:
            index: int
        
        received: list[TestEvent] = []
        
        class TestHandler:
            async def handle(self, event: TestEvent) -> None:
                received.append(event)
        
        bus: EventBus[TestEvent] = EventBus()
        bus.subscribe(TestEvent, TestHandler())
        
        for i in range(num_events):
            await bus.publish(TestEvent(index=i))
        
        assert len(received) == num_events
        for i, event in enumerate(received):
            assert event.index == i


# =============================================================================
# Property 14: Message Broker Topic Routing
# **Feature: infrastructure-generics-review-2025, Property 14: Message Broker Topic Routing**
# **Validates: Requirements 10.5**
# =============================================================================

class TestMessageBrokerTopicRouting:
    """Property tests for message broker topic routing.
    
    *For any* message published to a topic, all subscribers to that 
    topic should receive the message.
    """

    @pytest.mark.asyncio
    async def test_message_routed_to_correct_topic(self) -> None:
        """Messages are routed to correct topic subscribers."""
        from infrastructure.messaging.generics import InMemoryBroker
        from dataclasses import dataclass
        
        @dataclass
        class TestMessage:
            content: str
        
        topic1_messages: list[TestMessage] = []
        topic2_messages: list[TestMessage] = []
        
        class Topic1Handler:
            async def handle(self, message: TestMessage) -> None:
                topic1_messages.append(message)
        
        class Topic2Handler:
            async def handle(self, message: TestMessage) -> None:
                topic2_messages.append(message)
        
        broker: InMemoryBroker[TestMessage] = InMemoryBroker()
        await broker.subscribe("topic1", Topic1Handler())
        await broker.subscribe("topic2", Topic2Handler())
        
        # Publish to topic1
        msg1 = TestMessage(content="for topic1")
        await broker.publish("topic1", msg1)
        
        assert len(topic1_messages) == 1
        assert topic1_messages[0] == msg1
        assert len(topic2_messages) == 0

    @pytest.mark.asyncio
    async def test_multiple_subscribers_receive_message(self) -> None:
        """All subscribers to a topic receive the message."""
        from infrastructure.messaging.generics import InMemoryBroker
        from dataclasses import dataclass
        
        @dataclass
        class TestMessage:
            content: str
        
        handler1_messages: list[TestMessage] = []
        handler2_messages: list[TestMessage] = []
        
        class Handler1:
            async def handle(self, message: TestMessage) -> None:
                handler1_messages.append(message)
        
        class Handler2:
            async def handle(self, message: TestMessage) -> None:
                handler2_messages.append(message)
        
        broker: InMemoryBroker[TestMessage] = InMemoryBroker()
        await broker.subscribe("topic", Handler1())
        await broker.subscribe("topic", Handler2())
        
        msg = TestMessage(content="broadcast")
        await broker.publish("topic", msg)
        
        assert len(handler1_messages) == 1
        assert len(handler2_messages) == 1
        assert handler1_messages[0] == msg
        assert handler2_messages[0] == msg

    @given(
        topics=st.lists(
            st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=("L",))),
            min_size=2,
            max_size=5,
            unique=True,
        )
    )
    @pytest.mark.asyncio
    async def test_messages_isolated_between_topics(self, topics: list[str]) -> None:
        """Messages on different topics are isolated."""
        from infrastructure.messaging.generics import InMemoryBroker
        from dataclasses import dataclass
        
        @dataclass
        class TestMessage:
            topic: str
        
        received_by_topic: dict[str, list[TestMessage]] = {t: [] for t in topics}
        
        broker: InMemoryBroker[TestMessage] = InMemoryBroker()
        
        # Subscribe to each topic
        for topic in topics:
            class TopicHandler:
                def __init__(self, t: str):
                    self.topic = t
                
                async def handle(self, message: TestMessage) -> None:
                    received_by_topic[self.topic].append(message)
            
            await broker.subscribe(topic, TopicHandler(topic))
        
        # Publish to first topic only
        msg = TestMessage(topic=topics[0])
        await broker.publish(topics[0], msg)
        
        # Only first topic should have received the message
        assert len(received_by_topic[topics[0]]) == 1
        for topic in topics[1:]:
            assert len(received_by_topic[topic]) == 0

    @pytest.mark.asyncio
    async def test_get_messages_by_topic(self) -> None:
        """Broker tracks messages by topic."""
        from infrastructure.messaging.generics import InMemoryBroker
        from dataclasses import dataclass
        
        @dataclass
        class TestMessage:
            content: str
        
        broker: InMemoryBroker[TestMessage] = InMemoryBroker()
        
        msg1 = TestMessage(content="msg1")
        msg2 = TestMessage(content="msg2")
        msg3 = TestMessage(content="msg3")
        
        await broker.publish("topic1", msg1)
        await broker.publish("topic2", msg2)
        await broker.publish("topic1", msg3)
        
        topic1_messages = broker.get_messages("topic1")
        topic2_messages = broker.get_messages("topic2")
        all_messages = broker.get_messages()
        
        assert len(topic1_messages) == 2
        assert len(topic2_messages) == 1
        assert len(all_messages) == 3



# =============================================================================
# Property 15: Health Check Status Propagation
# **Feature: infrastructure-generics-review-2025, Property 15: Health Check Status Propagation**
# **Validates: Requirements 11.5**
# =============================================================================

class TestHealthCheckStatusPropagation:
    """Property tests for health check status propagation.
    
    *For any* composite health check, if any component is UNHEALTHY the 
    composite should be UNHEALTHY; if any is DEGRADED and none UNHEALTHY, 
    composite should be DEGRADED.
    """

    @pytest.mark.asyncio
    async def test_all_healthy_returns_healthy(self) -> None:
        """All healthy checks result in healthy composite."""
        from infrastructure.observability.generics import (
            CompositeHealthCheck,
            HealthCheckResult,
            HealthStatus,
        )
        
        class HealthyCheck:
            def __init__(self, name: str):
                self._name = name
            
            async def check(self) -> HealthCheckResult:
                return HealthCheckResult(status=HealthStatus.HEALTHY, name=self._name)
            
            @property
            def name(self) -> str:
                return self._name
        
        composite = CompositeHealthCheck("test")
        composite.add_check(HealthyCheck("check1"))
        composite.add_check(HealthyCheck("check2"))
        composite.add_check(HealthyCheck("check3"))
        
        result = await composite.check()
        
        assert result.status == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_any_unhealthy_returns_unhealthy(self) -> None:
        """Any unhealthy check results in unhealthy composite."""
        from infrastructure.observability.generics import (
            CompositeHealthCheck,
            HealthCheckResult,
            HealthStatus,
        )
        
        class HealthyCheck:
            def __init__(self, name: str):
                self._name = name
            
            async def check(self) -> HealthCheckResult:
                return HealthCheckResult(status=HealthStatus.HEALTHY, name=self._name)
            
            @property
            def name(self) -> str:
                return self._name
        
        class UnhealthyCheck:
            def __init__(self, name: str):
                self._name = name
            
            async def check(self) -> HealthCheckResult:
                return HealthCheckResult(status=HealthStatus.UNHEALTHY, name=self._name)
            
            @property
            def name(self) -> str:
                return self._name
        
        composite = CompositeHealthCheck("test")
        composite.add_check(HealthyCheck("check1"))
        composite.add_check(UnhealthyCheck("check2"))
        composite.add_check(HealthyCheck("check3"))
        
        result = await composite.check()
        
        assert result.status == HealthStatus.UNHEALTHY

    @pytest.mark.asyncio
    async def test_degraded_without_unhealthy_returns_degraded(self) -> None:
        """Degraded check without unhealthy results in degraded composite."""
        from infrastructure.observability.generics import (
            CompositeHealthCheck,
            HealthCheckResult,
            HealthStatus,
        )
        
        class HealthyCheck:
            def __init__(self, name: str):
                self._name = name
            
            async def check(self) -> HealthCheckResult:
                return HealthCheckResult(status=HealthStatus.HEALTHY, name=self._name)
            
            @property
            def name(self) -> str:
                return self._name
        
        class DegradedCheck:
            def __init__(self, name: str):
                self._name = name
            
            async def check(self) -> HealthCheckResult:
                return HealthCheckResult(status=HealthStatus.DEGRADED, name=self._name)
            
            @property
            def name(self) -> str:
                return self._name
        
        composite = CompositeHealthCheck("test")
        composite.add_check(HealthyCheck("check1"))
        composite.add_check(DegradedCheck("check2"))
        composite.add_check(HealthyCheck("check3"))
        
        result = await composite.check()
        
        assert result.status == HealthStatus.DEGRADED

    @pytest.mark.asyncio
    async def test_unhealthy_takes_precedence_over_degraded(self) -> None:
        """Unhealthy takes precedence over degraded."""
        from infrastructure.observability.generics import (
            CompositeHealthCheck,
            HealthCheckResult,
            HealthStatus,
        )
        
        class DegradedCheck:
            def __init__(self, name: str):
                self._name = name
            
            async def check(self) -> HealthCheckResult:
                return HealthCheckResult(status=HealthStatus.DEGRADED, name=self._name)
            
            @property
            def name(self) -> str:
                return self._name
        
        class UnhealthyCheck:
            def __init__(self, name: str):
                self._name = name
            
            async def check(self) -> HealthCheckResult:
                return HealthCheckResult(status=HealthStatus.UNHEALTHY, name=self._name)
            
            @property
            def name(self) -> str:
                return self._name
        
        composite = CompositeHealthCheck("test")
        composite.add_check(DegradedCheck("check1"))
        composite.add_check(UnhealthyCheck("check2"))
        composite.add_check(DegradedCheck("check3"))
        
        result = await composite.check()
        
        assert result.status == HealthStatus.UNHEALTHY

    @pytest.mark.asyncio
    async def test_empty_composite_is_healthy(self) -> None:
        """Empty composite health check is healthy."""
        from infrastructure.observability.generics import (
            CompositeHealthCheck,
            HealthStatus,
        )
        
        composite = CompositeHealthCheck("test")
        result = await composite.check()
        
        assert result.status == HealthStatus.HEALTHY



# =============================================================================
# Property 16: Rate Limiter Consistency
# **Feature: infrastructure-generics-review-2025, Property 16: Rate Limiter Consistency**
# **Validates: Requirements 12.2**
# =============================================================================

class TestRateLimiterConsistency:
    """Property tests for rate limiter consistency.
    
    *For any* rate limiter and key, the remaining count should decrease 
    by 1 after each allowed request until reaching 0.
    """

    @pytest.mark.asyncio
    async def test_remaining_decreases_on_allowed_request(self) -> None:
        """Remaining count decreases by 1 on each allowed request."""
        from infrastructure.security.generics import SlidingWindowLimiter
        
        limiter: SlidingWindowLimiter[str] = SlidingWindowLimiter(
            max_requests=5,
            window_seconds=60,
        )
        
        key = "test_user"
        
        # First request
        result1 = await limiter.check(key)
        assert result1.allowed is True
        assert result1.remaining == 4
        
        # Second request
        result2 = await limiter.check(key)
        assert result2.allowed is True
        assert result2.remaining == 3
        
        # Third request
        result3 = await limiter.check(key)
        assert result3.allowed is True
        assert result3.remaining == 2

    @pytest.mark.asyncio
    async def test_request_denied_when_limit_reached(self) -> None:
        """Request is denied when rate limit is reached."""
        from infrastructure.security.generics import SlidingWindowLimiter
        
        limiter: SlidingWindowLimiter[str] = SlidingWindowLimiter(
            max_requests=3,
            window_seconds=60,
        )
        
        key = "test_user"
        
        # Exhaust the limit
        for _ in range(3):
            result = await limiter.check(key)
            assert result.allowed is True
        
        # Next request should be denied
        result = await limiter.check(key)
        assert result.allowed is False
        assert result.remaining == 0
        assert result.retry_after is not None

    @given(max_requests=st.integers(min_value=1, max_value=10))
    @pytest.mark.asyncio
    async def test_exact_limit_requests_allowed(self, max_requests: int) -> None:
        """Exactly max_requests are allowed before denial."""
        from infrastructure.security.generics import SlidingWindowLimiter
        
        limiter: SlidingWindowLimiter[str] = SlidingWindowLimiter(
            max_requests=max_requests,
            window_seconds=60,
        )
        
        key = "test_user"
        allowed_count = 0
        
        for _ in range(max_requests + 5):
            result = await limiter.check(key)
            if result.allowed:
                allowed_count += 1
        
        assert allowed_count == max_requests

    @pytest.mark.asyncio
    async def test_reset_restores_limit(self) -> None:
        """Reset restores the rate limit."""
        from infrastructure.security.generics import SlidingWindowLimiter
        
        limiter: SlidingWindowLimiter[str] = SlidingWindowLimiter(
            max_requests=3,
            window_seconds=60,
        )
        
        key = "test_user"
        
        # Exhaust the limit
        for _ in range(3):
            await limiter.check(key)
        
        # Verify limit is exhausted
        result = await limiter.check(key)
        assert result.allowed is False
        
        # Reset
        await limiter.reset(key)
        
        # Should be allowed again
        result = await limiter.check(key)
        assert result.allowed is True
        assert result.remaining == 2

    @pytest.mark.asyncio
    async def test_different_keys_have_separate_limits(self) -> None:
        """Different keys have independent rate limits."""
        from infrastructure.security.generics import SlidingWindowLimiter
        
        limiter: SlidingWindowLimiter[str] = SlidingWindowLimiter(
            max_requests=2,
            window_seconds=60,
        )
        
        # Exhaust limit for user1
        for _ in range(2):
            await limiter.check("user1")
        
        result_user1 = await limiter.check("user1")
        assert result_user1.allowed is False
        
        # user2 should still have full limit
        result_user2 = await limiter.check("user2")
        assert result_user2.allowed is True
        assert result_user2.remaining == 1

    @pytest.mark.asyncio
    async def test_token_bucket_limiter_basic(self) -> None:
        """Token bucket limiter allows requests up to capacity."""
        from infrastructure.security.generics import TokenBucketLimiter
        
        limiter: TokenBucketLimiter[str] = TokenBucketLimiter(
            capacity=5,
            refill_rate=1.0,  # 1 token per second
        )
        
        key = "test_user"
        
        # Should allow up to capacity
        for i in range(5):
            result = await limiter.check(key)
            assert result.allowed is True
        
        # Next should be denied (no time for refill)
        result = await limiter.check(key)
        assert result.allowed is False



# =============================================================================
# Property 17: Priority Queue Ordering
# **Feature: infrastructure-generics-review-2025, Property 17: Priority Queue Ordering**
# **Validates: Requirements 13.5**
# =============================================================================

class TestPriorityQueueOrdering:
    """Property tests for priority queue ordering.
    
    *For any* priority job queue, dequeuing should always return the job 
    with the highest priority (lowest priority value).
    """

    @pytest.mark.asyncio
    async def test_dequeue_returns_highest_priority(self) -> None:
        """Dequeue returns job with lowest priority value (highest priority)."""
        from infrastructure.tasks.generics import PriorityJobQueue
        from dataclasses import dataclass
        
        @dataclass
        class TestJob:
            name: str
        
        queue: PriorityJobQueue[TestJob, int] = PriorityJobQueue()
        
        # Enqueue jobs with different priorities
        await queue.enqueue(TestJob(name="low"), priority=10)
        await queue.enqueue(TestJob(name="high"), priority=1)
        await queue.enqueue(TestJob(name="medium"), priority=5)
        
        # Dequeue should return in priority order
        result1 = await queue.dequeue()
        assert result1 is not None
        assert result1[1].name == "high"
        
        result2 = await queue.dequeue()
        assert result2 is not None
        assert result2[1].name == "medium"
        
        result3 = await queue.dequeue()
        assert result3 is not None
        assert result3[1].name == "low"

    @given(priorities=st.lists(st.integers(min_value=0, max_value=100), min_size=1, max_size=20))
    @pytest.mark.asyncio
    async def test_dequeue_order_matches_sorted_priorities(self, priorities: list[int]) -> None:
        """Dequeue order matches sorted priority order."""
        from infrastructure.tasks.generics import PriorityJobQueue
        from dataclasses import dataclass
        
        @dataclass
        class TestJob:
            priority: int
        
        queue: PriorityJobQueue[TestJob, int] = PriorityJobQueue()
        
        # Enqueue all jobs
        for p in priorities:
            await queue.enqueue(TestJob(priority=p), priority=p)
        
        # Dequeue all and collect priorities
        dequeued_priorities = []
        while queue.size > 0:
            result = await queue.dequeue()
            if result:
                dequeued_priorities.append(result[1].priority)
        
        # Should be in sorted order
        assert dequeued_priorities == sorted(priorities)

    @pytest.mark.asyncio
    async def test_same_priority_fifo_order(self) -> None:
        """Jobs with same priority are dequeued in FIFO order."""
        from infrastructure.tasks.generics import PriorityJobQueue
        from dataclasses import dataclass
        
        @dataclass
        class TestJob:
            name: str
        
        queue: PriorityJobQueue[TestJob, int] = PriorityJobQueue()
        
        # Enqueue jobs with same priority
        await queue.enqueue(TestJob(name="first"), priority=5)
        await queue.enqueue(TestJob(name="second"), priority=5)
        await queue.enqueue(TestJob(name="third"), priority=5)
        
        # Should dequeue in FIFO order
        result1 = await queue.dequeue()
        assert result1 is not None
        assert result1[1].name == "first"
        
        result2 = await queue.dequeue()
        assert result2 is not None
        assert result2[1].name == "second"
        
        result3 = await queue.dequeue()
        assert result3 is not None
        assert result3[1].name == "third"

    @pytest.mark.asyncio
    async def test_peek_does_not_remove(self) -> None:
        """Peek returns highest priority without removing."""
        from infrastructure.tasks.generics import PriorityJobQueue
        from dataclasses import dataclass
        
        @dataclass
        class TestJob:
            name: str
        
        queue: PriorityJobQueue[TestJob, int] = PriorityJobQueue()
        
        await queue.enqueue(TestJob(name="job1"), priority=5)
        await queue.enqueue(TestJob(name="job2"), priority=1)
        
        # Peek should return highest priority
        peek_result = await queue.peek()
        assert peek_result is not None
        assert peek_result[1].name == "job2"
        
        # Size should be unchanged
        assert queue.size == 2
        
        # Dequeue should return same job
        dequeue_result = await queue.dequeue()
        assert dequeue_result is not None
        assert dequeue_result[1].name == "job2"
        assert queue.size == 1

    @pytest.mark.asyncio
    async def test_empty_queue_returns_none(self) -> None:
        """Empty queue returns None on dequeue and peek."""
        from infrastructure.tasks.generics import PriorityJobQueue
        from dataclasses import dataclass
        
        @dataclass
        class TestJob:
            name: str
        
        queue: PriorityJobQueue[TestJob, int] = PriorityJobQueue()
        
        assert await queue.dequeue() is None
        assert await queue.peek() is None
        assert queue.size == 0

    @given(num_jobs=st.integers(min_value=1, max_value=50))
    @pytest.mark.asyncio
    async def test_size_tracks_correctly(self, num_jobs: int) -> None:
        """Queue size is tracked correctly."""
        from infrastructure.tasks.generics import PriorityJobQueue
        from dataclasses import dataclass
        
        @dataclass
        class TestJob:
            index: int
        
        queue: PriorityJobQueue[TestJob, int] = PriorityJobQueue()
        
        # Enqueue
        for i in range(num_jobs):
            await queue.enqueue(TestJob(index=i), priority=i)
            assert queue.size == i + 1
        
        # Dequeue
        for i in range(num_jobs):
            await queue.dequeue()
            assert queue.size == num_jobs - i - 1

