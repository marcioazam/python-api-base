"""Nonce store for replay protection.

**Feature: full-codebase-review-2025, Task 1.6: Refactor request_signing**
**Validates: Requirements 9.2**
"""

import time


class NonceStore:
    """In-memory nonce store for replay protection."""

    def __init__(self, max_age: int = 300) -> None:
        """Initialize nonce store.

        Args:
            max_age: Maximum age of nonces to keep (seconds).
        """
        self._nonces: dict[str, int] = {}
        self._max_age = max_age

    def check_and_store(self, nonce: str, timestamp: int) -> bool:
        """Check if nonce is new and store it.

        Args:
            nonce: Request nonce.
            timestamp: Request timestamp.

        Returns:
            True if nonce is new, False if already used.
        """
        self._cleanup()
        if nonce in self._nonces:
            return False
        self._nonces[nonce] = timestamp
        return True

    def _cleanup(self) -> None:
        """Remove expired nonces."""
        current_time = int(time.time())
        cutoff = current_time - self._max_age
        expired = [k for k, v in self._nonces.items() if v < cutoff]
        for key in expired:
            del self._nonces[key]

    def clear(self) -> None:
        """Clear all stored nonces."""
        self._nonces.clear()

    @property
    def size(self) -> int:
        """Get number of stored nonces."""
        return len(self._nonces)
