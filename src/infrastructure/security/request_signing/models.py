"""Request signing models.

**Feature: full-codebase-review-2025, Task 1.6: Refactor request_signing**
**Validates: Requirements 9.2**
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SignedRequest:
    """Signed request data.

    Attributes:
        signature: HMAC signature.
        timestamp: Request timestamp.
        nonce: Unique nonce for replay protection.
        canonical_string: The string that was signed.
    """

    signature: str
    timestamp: int
    nonce: str
    canonical_string: str
