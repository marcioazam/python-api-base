"""Event Sourcing exceptions.

**Feature: code-review-refactoring, Task 1.2: Extract exceptions module**
**Validates: Requirements 2.1**
"""


class ConcurrencyError(Exception):
    """Raised when optimistic concurrency check fails.

    This error occurs when attempting to save an aggregate with an
    expected version that doesn't match the current version in the store.

    **Feature: shared-modules-phase2, Property 9: ConcurrencyError Message Content**
    **Validates: Requirements 5.2**

    Attributes:
        expected_version: The version that was expected.
        actual_version: The actual version found in the store.
    """

    def __init__(
        self,
        message: str,
        expected_version: int | None = None,
        actual_version: int | None = None,
    ) -> None:
        """Initialize concurrency error.

        Args:
            message: Human-readable error message.
            expected_version: The version that was expected.
            actual_version: The actual version found in the store.
        """
        self.expected_version = expected_version
        self.actual_version = actual_version
        if expected_version is not None and actual_version is not None:
            message = f"{message} (expected: {expected_version}, actual: {actual_version})"
        super().__init__(message)
