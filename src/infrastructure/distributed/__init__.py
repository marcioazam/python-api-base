"""Distributed systems infrastructure module.

Provides distributed coordination primitives including locks and leader election.

**Feature: python-api-base-2025-review**
"""

from src.infrastructure.distributed.distributed_lock import (
    DistributedLock,
    LockAcquisitionError,
)
from src.infrastructure.distributed.leader_election import (
    LeaderElection,
    LeaderElectionConfig,
)

__all__ = [
    "DistributedLock",
    "LockAcquisitionError",
    "LeaderElection",
    "LeaderElectionConfig",
]
