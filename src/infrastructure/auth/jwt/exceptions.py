"""JWT-specific exceptions.

**Feature: api-base-score-100**
**Validates: Requirements 1.1, 4.4**
"""


class InvalidKeyError(Exception):
    """Raised when JWT key format is invalid."""

    def __init__(self, message: str = "Invalid key format") -> None:
        super().__init__(message)
        self.message = message


class AlgorithmMismatchError(Exception):
    """Raised when token algorithm doesn't match expected."""

    def __init__(self, expected: str, received: str) -> None:
        message = f"Algorithm mismatch: expected {expected}, got {received}"
        super().__init__(message)
        self.expected = expected
        self.received = received
