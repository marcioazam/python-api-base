"""Connection pool statistics model.

**Feature: full-codebase-review-2025, Task 1.1: Refactor connection_pool**
**Validates: Requirements 9.2**
"""

from pydantic import BaseModel


class PoolStats(BaseModel):
    """Pool statistics.

    Attributes:
        total_connections: Total connections in pool.
        idle_connections: Number of idle connections.
        in_use_connections: Number of connections in use.
        unhealthy_connections: Number of unhealthy connections.
        total_acquires: Total number of acquires.
        total_releases: Total number of releases.
        total_timeouts: Total number of acquire timeouts.
        avg_wait_time_ms: Average wait time in milliseconds.
    """

    total_connections: int = 0
    idle_connections: int = 0
    in_use_connections: int = 0
    unhealthy_connections: int = 0
    total_acquires: int = 0
    total_releases: int = 0
    total_timeouts: int = 0
    avg_wait_time_ms: float = 0.0

    def validate_invariant(self) -> bool:
        """Validate that counters are consistent.

        **Feature: shared-modules-phase2, Property 1: Pool Counter Invariant**
        **Validates: Requirements 2.3**

        Returns:
            True if invariant holds (idle + in_use + unhealthy == total).
        """
        return (
            self.idle_connections + self.in_use_connections + self.unhealthy_connections
        ) == self.total_connections
