"""Resilience patterns module.

**Feature: python-api-base-2025-generics-audit**
**Validates: Requirements 16.1-16.5**
"""

from .patterns import (
    BackoffStrategy,
    Bulkhead,
    BulkheadConfig,
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    ExponentialBackoff,
    Fallback,
    Retry,
    RetryConfig,
    Timeout,
    TimeoutConfig,
)

__all__ = [
    "BackoffStrategy",
    "Bulkhead",
    "BulkheadConfig",
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitState",
    "ExponentialBackoff",
    "Fallback",
    "Retry",
    "RetryConfig",
    "Timeout",
    "TimeoutConfig",
]
