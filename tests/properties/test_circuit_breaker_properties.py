"""Property-based tests for Circuit Breaker pattern.

**Feature: api-architecture-analysis**
**Validates: Requirements 9.4**
"""

from datetime import datetime, timedelta, timezone

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from my_app.infrastructure.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitState,
)
from dataclasses import dataclass
from datetime import timedelta

@dataclass
class CircuitBreakerConfig:
    """Config for circuit breaker tests."""
    failure_threshold: int = 5
    success_threshold: int = 2
    timeout: timedelta = timedelta(seconds=30)
    half_open_max_calls: int = 3


# Generators for CircuitBreakerConfig
@st.composite
def circuit_breaker_configs(draw: st.DrawFn) -> CircuitBreakerConfig:
    """Generate valid CircuitBreakerConfig instances."""
    failure_threshold = draw(st.integers(min_value=1, max_value=10))
    success_threshold = draw(st.integers(min_value=1, max_value=5))
    timeout_seconds = draw(st.integers(min_value=1, max_value=60))
    half_open_max_calls = draw(st.integers(min_value=1, max_value=10))
    
    return CircuitBreakerConfig(
        failure_threshold=failure_threshold,
        success_threshold=success_threshold,
        timeout=timedelta(seconds=timeout_seconds),
        half_open_max_calls=half_open_max_calls,
    )


@st.composite
def circuit_breaker_names(draw: st.DrawFn) -> str:
    """Generate valid circuit breaker names."""
    return draw(st.text(
        alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="_-"),
        min_size=1,
        max_size=50,
    ).filter(lambda x: x.strip() != ""))


class TestCircuitBreakerStateTransitions:
    """Property tests for circuit breaker state transitions.
    
    **Feature: api-architecture-analysis, Property 23: Circuit Breaker State Transitions**
    **Validates: Requirements 9.4**
    """

    @given(
        failure_threshold=st.integers(min_value=1, max_value=10),
        extra_failures=st.integers(min_value=0, max_value=5),
    )
    @settings(max_examples=100)
    def test_circuit_opens_after_failure_threshold(
        self,
        failure_threshold: int,
        extra_failures: int,
    ) -> None:
        """
        **Feature: api-architecture-analysis, Property 23: Circuit Breaker State Transitions**
        **Validates: Requirements 9.4**
        
        For any circuit breaker, after exactly failure_threshold consecutive failures,
        the state SHALL change to OPEN.
        """
        config = CircuitBreakerConfig(failure_threshold=failure_threshold)
        cb = CircuitBreaker("test", config)
        
        # Initial state should be CLOSED
        assert cb._state == CircuitState.CLOSED
        
        # Record failures up to threshold
        total_failures = failure_threshold + extra_failures
        for i in range(total_failures):
            cb._record_failure()
            
            if i + 1 >= failure_threshold:
                # After reaching threshold, should be OPEN
                assert cb._state == CircuitState.OPEN, (
                    f"Expected OPEN after {i + 1} failures with threshold {failure_threshold}"
                )
            else:
                # Before threshold, should still be CLOSED
                assert cb._state == CircuitState.CLOSED, (
                    f"Expected CLOSED after {i + 1} failures with threshold {failure_threshold}"
                )

    @given(
        failure_threshold=st.integers(min_value=2, max_value=10),
        failures_before_success=st.integers(min_value=1, max_value=9),
    )
    @settings(max_examples=100)
    def test_success_resets_failure_count(
        self,
        failure_threshold: int,
        failures_before_success: int,
    ) -> None:
        """
        **Feature: api-architecture-analysis, Property 23: Circuit Breaker State Transitions**
        **Validates: Requirements 9.4**
        
        For any circuit breaker in CLOSED state, a success SHALL reset the failure count.
        """
        assume(failures_before_success < failure_threshold)
        
        config = CircuitBreakerConfig(failure_threshold=failure_threshold)
        cb = CircuitBreaker("test", config)
        
        # Record some failures (but not enough to trip)
        for _ in range(failures_before_success):
            cb._record_failure()
        
        assert cb._state == CircuitState.CLOSED
        assert cb._failure_count == failures_before_success
        
        # Record a success
        cb._record_success()
        
        # Failure count should be reset
        assert cb._failure_count == 0
        assert cb._state == CircuitState.CLOSED


class TestCircuitBreakerHalfOpenRecovery:
    """Property tests for half-open recovery behavior.
    
    **Feature: api-architecture-analysis**
    **Validates: Requirements 9.4**
    """

    @given(
        success_threshold=st.integers(min_value=1, max_value=5),
        extra_successes=st.integers(min_value=0, max_value=3),
    )
    @settings(max_examples=100)
    def test_circuit_closes_after_success_threshold_in_half_open(
        self,
        success_threshold: int,
        extra_successes: int,
    ) -> None:
        """
        **Feature: api-architecture-analysis, Property 23: Circuit Breaker State Transitions**
        **Validates: Requirements 9.4**
        
        For any circuit breaker in HALF_OPEN state, after success_threshold consecutive
        successes, the state SHALL change to CLOSED.
        """
        config = CircuitBreakerConfig(
            failure_threshold=1,
            success_threshold=success_threshold,
        )
        cb = CircuitBreaker("test", config)
        
        # Force into HALF_OPEN state
        cb._state = CircuitState.HALF_OPEN
        cb._success_count = 0
        
        # Record successes
        total_successes = success_threshold + extra_successes
        for i in range(total_successes):
            cb._record_success()
            
            if i + 1 >= success_threshold:
                # After reaching threshold, should be CLOSED
                assert cb._state == CircuitState.CLOSED, (
                    f"Expected CLOSED after {i + 1} successes with threshold {success_threshold}"
                )
                break  # Once closed, stop testing
            else:
                # Before threshold, should still be HALF_OPEN
                assert cb._state == CircuitState.HALF_OPEN, (
                    f"Expected HALF_OPEN after {i + 1} successes with threshold {success_threshold}"
                )

    @given(config=circuit_breaker_configs())
    @settings(max_examples=100)
    def test_failure_in_half_open_trips_circuit(
        self,
        config: CircuitBreakerConfig,
    ) -> None:
        """
        **Feature: api-architecture-analysis, Property 23: Circuit Breaker State Transitions**
        **Validates: Requirements 9.4**
        
        For any circuit breaker in HALF_OPEN state, a single failure SHALL trip
        the circuit back to OPEN.
        """
        cb = CircuitBreaker("test", config)
        
        # Force into HALF_OPEN state
        cb._state = CircuitState.HALF_OPEN
        cb._success_count = 0
        
        # Record a failure
        cb._record_failure()
        
        # Should be back to OPEN
        assert cb._state == CircuitState.OPEN


class TestCircuitBreakerTimeoutReset:
    """Property tests for timeout-based state transitions.
    
    **Feature: api-architecture-analysis**
    **Validates: Requirements 9.4**
    """

    @given(timeout_seconds=st.integers(min_value=1, max_value=60))
    @settings(max_examples=100)
    def test_circuit_transitions_to_half_open_after_timeout(
        self,
        timeout_seconds: int,
    ) -> None:
        """
        **Feature: api-architecture-analysis, Property 23: Circuit Breaker State Transitions**
        **Validates: Requirements 9.4**
        
        For any circuit breaker in OPEN state, after the timeout period has elapsed,
        accessing the state SHALL transition it to HALF_OPEN.
        """
        config = CircuitBreakerConfig(
            failure_threshold=1,
            timeout=timedelta(seconds=timeout_seconds),
        )
        cb = CircuitBreaker("test", config)
        
        # Trip the circuit
        cb._record_failure()
        assert cb._state == CircuitState.OPEN
        
        # Simulate time passing by setting last_failure_time in the past
        cb._last_failure_time = datetime.now(timezone.utc) - timedelta(seconds=timeout_seconds + 1)
        
        # Accessing state property should trigger transition
        current_state = cb.state
        
        assert current_state == CircuitState.HALF_OPEN

    @given(timeout_seconds=st.integers(min_value=2, max_value=60))
    @settings(max_examples=100)
    def test_circuit_stays_open_before_timeout(
        self,
        timeout_seconds: int,
    ) -> None:
        """
        **Feature: api-architecture-analysis, Property 23: Circuit Breaker State Transitions**
        **Validates: Requirements 9.4**
        
        For any circuit breaker in OPEN state, before the timeout period has elapsed,
        the state SHALL remain OPEN.
        """
        config = CircuitBreakerConfig(
            failure_threshold=1,
            timeout=timedelta(seconds=timeout_seconds),
        )
        cb = CircuitBreaker("test", config)
        
        # Trip the circuit
        cb._record_failure()
        assert cb._state == CircuitState.OPEN
        
        # Set last_failure_time to just now (within timeout)
        cb._last_failure_time = datetime.now(timezone.utc)
        
        # Accessing state property should NOT trigger transition
        current_state = cb.state
        
        assert current_state == CircuitState.OPEN


class TestCircuitBreakerCanExecute:
    """Property tests for execution permission logic.
    
    **Feature: api-architecture-analysis**
    **Validates: Requirements 9.4**
    """

    @given(config=circuit_breaker_configs())
    @settings(max_examples=100)
    def test_can_execute_in_closed_state(
        self,
        config: CircuitBreakerConfig,
    ) -> None:
        """
        For any circuit breaker in CLOSED state, _can_execute SHALL return True.
        """
        cb = CircuitBreaker("test", config)
        assert cb._state == CircuitState.CLOSED
        assert cb._can_execute() is True

    @given(config=circuit_breaker_configs())
    @settings(max_examples=100)
    def test_cannot_execute_in_open_state(
        self,
        config: CircuitBreakerConfig,
    ) -> None:
        """
        For any circuit breaker in OPEN state (within timeout), _can_execute SHALL return False.
        """
        cb = CircuitBreaker("test", config)
        
        # Force into OPEN state
        cb._state = CircuitState.OPEN
        cb._last_failure_time = datetime.now(timezone.utc)  # Recent failure, within timeout
        
        assert cb._can_execute() is False

    @given(
        half_open_max_calls=st.integers(min_value=1, max_value=10),
        calls_to_make=st.integers(min_value=1, max_value=15),
    )
    @settings(max_examples=100)
    def test_limited_calls_in_half_open_state(
        self,
        half_open_max_calls: int,
        calls_to_make: int,
    ) -> None:
        """
        For any circuit breaker in HALF_OPEN state, only half_open_max_calls
        SHALL be allowed before rejecting further calls.
        """
        config = CircuitBreakerConfig(
            failure_threshold=1,
            half_open_max_calls=half_open_max_calls,
        )
        cb = CircuitBreaker("test", config)
        
        # Force into HALF_OPEN state
        cb._state = CircuitState.HALF_OPEN
        cb._half_open_calls = 0
        
        allowed_count = 0
        for _ in range(calls_to_make):
            if cb._can_execute():
                allowed_count += 1
        
        # Should allow exactly half_open_max_calls
        assert allowed_count == min(calls_to_make, half_open_max_calls)
