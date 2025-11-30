"""Leader Election implementation for single-instance tasks.

Provides leader election for distributed systems.

**Feature: api-architecture-analysis, Property 11: Leader election**
**Validates: Requirements 6.4**
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any
from collections.abc import Callable, Awaitable
import uuid


class LeaderState(str, Enum):
    """State of a leader election participant."""

    FOLLOWER = "follower"
    CANDIDATE = "candidate"
    LEADER = "leader"


@dataclass(slots=True)
class LeaderInfo:
    """Information about the current leader."""

    node_id: str
    elected_at: datetime
    lease_expires_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_lease_valid(self) -> bool:
        """Check if lease is still valid."""
        return datetime.now(timezone.utc) < self.lease_expires_at

    @property
    def remaining_lease_seconds(self) -> float:
        """Get remaining lease time in seconds."""
        remaining = (self.lease_expires_at - datetime.now(timezone.utc)).total_seconds()
        return max(0, remaining)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "node_id": self.node_id,
            "elected_at": self.elected_at.isoformat(),
            "lease_expires_at": self.lease_expires_at.isoformat(),
            "is_lease_valid": self.is_lease_valid,
            "remaining_lease_seconds": self.remaining_lease_seconds,
            "metadata": self.metadata,
        }


class LeaderElectionBackend(ABC):
    """Abstract backend for leader election."""

    @abstractmethod
    async def try_acquire_leadership(
        self,
        election_name: str,
        node_id: str,
        lease_duration: timedelta,
    ) -> bool:
        """Try to acquire leadership."""
        ...

    @abstractmethod
    async def renew_leadership(
        self,
        election_name: str,
        node_id: str,
        lease_duration: timedelta,
    ) -> bool:
        """Renew leadership lease."""
        ...

    @abstractmethod
    async def release_leadership(
        self,
        election_name: str,
        node_id: str,
    ) -> bool:
        """Release leadership."""
        ...

    @abstractmethod
    async def get_leader(self, election_name: str) -> LeaderInfo | None:
        """Get current leader info."""
        ...


class InMemoryLeaderElectionBackend(LeaderElectionBackend):
    """In-memory implementation for testing."""

    def __init__(self):
        self._leaders: dict[str, LeaderInfo] = {}
        self._lock = asyncio.Lock()

    async def try_acquire_leadership(
        self,
        election_name: str,
        node_id: str,
        lease_duration: timedelta,
    ) -> bool:
        """Try to acquire leadership."""
        async with self._lock:
            current = self._leaders.get(election_name)
            if current and current.is_lease_valid and current.node_id != node_id:
                return False

            now = datetime.now(timezone.utc)
            self._leaders[election_name] = LeaderInfo(
                node_id=node_id,
                elected_at=now,
                lease_expires_at=now + lease_duration,
            )
            return True

    async def renew_leadership(
        self,
        election_name: str,
        node_id: str,
        lease_duration: timedelta,
    ) -> bool:
        """Renew leadership lease."""
        async with self._lock:
            current = self._leaders.get(election_name)
            if not current or current.node_id != node_id:
                return False

            now = datetime.now(timezone.utc)
            current.lease_expires_at = now + lease_duration
            return True

    async def release_leadership(
        self,
        election_name: str,
        node_id: str,
    ) -> bool:
        """Release leadership."""
        async with self._lock:
            current = self._leaders.get(election_name)
            if not current or current.node_id != node_id:
                return False

            del self._leaders[election_name]
            return True

    async def get_leader(self, election_name: str) -> LeaderInfo | None:
        """Get current leader info."""
        async with self._lock:
            leader = self._leaders.get(election_name)
            if leader and leader.is_lease_valid:
                return leader
            return None


LeaderCallback = Callable[[], Awaitable[None]]


class LeaderElection:
    """Leader election coordinator."""

    def __init__(
        self,
        backend: LeaderElectionBackend,
        election_name: str,
        node_id: str | None = None,
        lease_duration: timedelta = timedelta(seconds=30),
        renewal_interval: timedelta = timedelta(seconds=10),
    ):
        self._backend = backend
        self._election_name = election_name
        self._node_id = node_id or str(uuid.uuid4())
        self._lease_duration = lease_duration
        self._renewal_interval = renewal_interval
        self._state = LeaderState.FOLLOWER
        self._running = False
        self._task: asyncio.Task[None] | None = None
        self._on_elected: LeaderCallback | None = None
        self._on_demoted: LeaderCallback | None = None

    @property
    def node_id(self) -> str:
        """Get this node's ID."""
        return self._node_id

    @property
    def state(self) -> LeaderState:
        """Get current state."""
        return self._state

    @property
    def is_leader(self) -> bool:
        """Check if this node is the leader."""
        return self._state == LeaderState.LEADER

    def on_elected(self, callback: LeaderCallback) -> None:
        """Set callback for when this node becomes leader."""
        self._on_elected = callback

    def on_demoted(self, callback: LeaderCallback) -> None:
        """Set callback for when this node loses leadership."""
        self._on_demoted = callback

    async def start(self) -> None:
        """Start participating in leader election."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._election_loop())

    async def stop(self) -> None:
        """Stop participating in leader election."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self._state == LeaderState.LEADER:
            await self._backend.release_leadership(
                self._election_name, self._node_id
            )
            self._state = LeaderState.FOLLOWER

    async def _election_loop(self) -> None:
        """Main election loop."""
        while self._running:
            try:
                if self._state == LeaderState.LEADER:
                    renewed = await self._backend.renew_leadership(
                        self._election_name,
                        self._node_id,
                        self._lease_duration,
                    )
                    if not renewed:
                        self._state = LeaderState.FOLLOWER
                        if self._on_demoted:
                            await self._on_demoted()
                else:
                    acquired = await self._backend.try_acquire_leadership(
                        self._election_name,
                        self._node_id,
                        self._lease_duration,
                    )
                    if acquired:
                        self._state = LeaderState.LEADER
                        if self._on_elected:
                            await self._on_elected()

                await asyncio.sleep(self._renewal_interval.total_seconds())
            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(1)

    async def get_leader(self) -> LeaderInfo | None:
        """Get current leader info."""
        return await self._backend.get_leader(self._election_name)

    async def force_election(self) -> bool:
        """Force a new election by releasing current leadership."""
        if self._state == LeaderState.LEADER:
            released = await self._backend.release_leadership(
                self._election_name, self._node_id
            )
            if released:
                self._state = LeaderState.FOLLOWER
                if self._on_demoted:
                    await self._on_demoted()
            return released
        return False
