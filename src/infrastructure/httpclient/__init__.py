"""Generic HTTP client infrastructure with PEP 695 type parameters.

**Feature: enterprise-generics-2025**
**Requirement: R9 - Generic HTTP Client with Resilience**

Exports:
    - HttpClient[TRequest, TResponse]: Generic HTTP client
    - HttpClientConfig: Configuration
    - HttpError: Base error class
    - TimeoutError: Timeout error
    - ValidationError: Response validation error
"""

from infrastructure.httpclient.client import (
    HttpClient,
    HttpClientConfig,
    HttpError,
    TimeoutError,
    ValidationError,
    RetryPolicy,
)

__all__ = [
    "HttpClient",
    "HttpClientConfig",
    "HttpError",
    "TimeoutError",
    "ValidationError",
    "RetryPolicy",
]
