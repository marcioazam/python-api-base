"""Generic HTTP client infrastructure with PEP 695 type parameters.

**Feature: enterprise-generics-2025**
**Requirement: R9 - Generic HTTP Client with Resilience**

Exports:
    - HttpClient[TRequest, TResponse]: Generic HTTP client
    - HttpClientConfig: Configuration
    - HttpError: Base error class
    - TimeoutError: Timeout error
    - ValidationError: Response validation error
    - CircuitBreakerError: Circuit breaker error
    - RetryPolicy: Retry policy configuration
    - CircuitState: Circuit breaker states
"""

from infrastructure.httpclient.client import HttpClient
from infrastructure.httpclient.errors import (
    CircuitBreakerError,
    HttpError,
    TimeoutError,
    ValidationError,
)
from infrastructure.httpclient.resilience import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    HttpClientConfig,
    RetryPolicy,
)

__all__ = [
    # Client
    "HttpClient",
    # Configuration
    "HttpClientConfig",
    "RetryPolicy",
    "CircuitBreakerConfig",
    # Errors
    "HttpError",
    "TimeoutError",
    "ValidationError",
    "CircuitBreakerError",
    # Resilience
    "CircuitBreaker",
    "CircuitState",
]
