"""Connection pool error classes.

**Feature: full-codebase-review-2025, Task 1.1: Refactor connection_pool**
**Validates: Requirements 9.2**
"""


class PoolError(Exception):
    """Base pool error."""

    def __init__(self, message: str, error_code: str = "POOL_ERROR") -> None:
        super().__init__(message)
        self.error_code = error_code


class PoolExhaustedError(PoolError):
    """Pool exhausted error."""

    def __init__(self) -> None:
        super().__init__("Connection pool exhausted", "POOL_EXHAUSTED")


class AcquireTimeoutError(PoolError):
    """Acquire timeout error."""

    def __init__(self, timeout: float) -> None:
        super().__init__(f"Acquire timeout after {timeout}s", "ACQUIRE_TIMEOUT")
        self.timeout = timeout


class ConnectionError(PoolError):
    """Connection error."""

    def __init__(self, message: str) -> None:
        super().__init__(message, "CONNECTION_ERROR")
