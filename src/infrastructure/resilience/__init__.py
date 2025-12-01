"""Resilience patterns for fault-tolerant applications.

Provides decorators and utilities for:
- Retry with exponential backoff
- Circuit breaker pattern
- Timeout handling
"""

from src.infrastructure.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitOpenError,
    CircuitState,
    circuit_breaker,
    get_circuit_breaker,
)
from src.infrastructure.resilience.retry import (
    RetryExhaustedError,
    retry,
    retry_sync,
)
from src.infrastructure.resilience.timeout import (
    TimeoutError,
    timeout,
    with_timeout,
)

__all__ = [
    # Retry
    "retry",
    "retry_sync",
    "RetryExhaustedError",
    # Circuit Breaker
    "circuit_breaker",
    "CircuitBreaker",
    "CircuitState",
    "CircuitOpenError",
    "get_circuit_breaker",
    # Timeout
    "timeout",
    "with_timeout",
    "TimeoutError",
]
