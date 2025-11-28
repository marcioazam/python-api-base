"""Event Sourcing exceptions.

**Feature: code-review-refactoring, Task 1.2: Extract exceptions module**
**Validates: Requirements 2.1**
"""


class ConcurrencyError(Exception):
    """Raised when optimistic concurrency check fails.

    This error occurs when attempting to save an aggregate with an
    expected version that doesn't match the current version in the store.
    """

    pass
