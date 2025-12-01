"""Request signing error classes.

**Feature: full-codebase-review-2025, Task 1.6: Refactor request_signing**
**Validates: Requirements 9.2**
"""


class SignatureError(Exception):
    """Base signature error."""

    def __init__(self, message: str, error_code: str = "SIGNATURE_ERROR") -> None:
        super().__init__(message)
        self.error_code = error_code


class InvalidSignatureError(SignatureError):
    """Invalid signature error."""

    def __init__(self, reason: str = "Signature verification failed") -> None:
        super().__init__(reason, "INVALID_SIGNATURE")


class ExpiredTimestampError(SignatureError):
    """Expired timestamp error."""

    def __init__(self, timestamp: int, tolerance: int) -> None:
        super().__init__(
            f"Timestamp {timestamp} is outside tolerance of {tolerance}s",
            "EXPIRED_TIMESTAMP",
        )
        self.timestamp = timestamp
        self.tolerance = tolerance


class ReplayedRequestError(SignatureError):
    """Replayed request error (nonce reuse)."""

    def __init__(self, nonce: str) -> None:
        super().__init__(f"Nonce {nonce} has already been used", "REPLAYED_REQUEST")
        self.nonce = nonce
