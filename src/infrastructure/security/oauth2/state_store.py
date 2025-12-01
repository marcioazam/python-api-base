"""OAuth2 state storage.

**Feature: code-review-refactoring, Task 5.5: Extract state_store module**
**Validates: Requirements 4.1**
"""

from typing import Protocol, runtime_checkable

from .models import OAuthState


@runtime_checkable
class StateStore(Protocol):
    """Protocol for OAuth state storage."""

    async def save_state(self, state: OAuthState) -> None:
        """Save OAuth state."""
        ...

    async def get_state(self, state_id: str) -> OAuthState | None:
        """Retrieve OAuth state by ID."""
        ...

    async def delete_state(self, state_id: str) -> None:
        """Delete OAuth state."""
        ...


class InMemoryStateStore:
    """In-memory OAuth state store for development/testing."""

    # Auto-cleanup threshold
    AUTO_CLEANUP_THRESHOLD = 100

    def __init__(self) -> None:
        self._states: dict[str, OAuthState] = {}

    async def save_state(self, state: OAuthState) -> None:
        """Save OAuth state with automatic cleanup when store grows large."""
        # Auto-cleanup when threshold exceeded
        if len(self._states) >= self.AUTO_CLEANUP_THRESHOLD:
            self.clear_expired()
        self._states[state.state] = state

    async def get_state(self, state_id: str) -> OAuthState | None:
        """Retrieve OAuth state by ID."""
        return self._states.get(state_id)

    async def delete_state(self, state_id: str) -> None:
        """Delete OAuth state."""
        self._states.pop(state_id, None)

    def clear_expired(self, max_age_seconds: int = 600) -> int:
        """Remove expired states.

        Args:
            max_age_seconds: Maximum age in seconds.

        Returns:
            Number of states removed.
        """
        expired = [
            k for k, v in self._states.items() if v.is_expired(max_age_seconds)
        ]
        for key in expired:
            del self._states[key]
        return len(expired)
