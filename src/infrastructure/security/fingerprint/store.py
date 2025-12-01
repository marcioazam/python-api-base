"""Fingerprint storage backends.

**Feature: file-size-compliance-phase2, Task 2.6**
**Validates: Requirements 1.6, 5.1, 5.2, 5.3**
"""

from typing import Protocol, runtime_checkable

from .enums import FingerprintComponent
from .models import Fingerprint


@runtime_checkable
class FingerprintStore(Protocol):
    """Protocol for fingerprint storage."""

    async def get(self, fingerprint_id: str) -> Fingerprint | None: ...
    async def save(self, fingerprint: Fingerprint) -> None: ...
    async def get_by_ip(self, ip_address: str) -> list[Fingerprint]: ...
    async def get_recent(self, limit: int = 100) -> list[Fingerprint]: ...


class InMemoryFingerprintStore:
    """In-memory implementation of FingerprintStore."""

    def __init__(self) -> None:
        self._fingerprints: dict[str, Fingerprint] = {}
        self._by_ip: dict[str, list[str]] = {}

    async def get(self, fingerprint_id: str) -> Fingerprint | None:
        """Get fingerprint by ID."""
        return self._fingerprints.get(fingerprint_id)

    async def save(self, fingerprint: Fingerprint) -> None:
        """Save a fingerprint."""
        self._fingerprints[fingerprint.fingerprint_id] = fingerprint
        ip = fingerprint.components.get(FingerprintComponent.IP_ADDRESS, "")
        if ip:
            if ip not in self._by_ip:
                self._by_ip[ip] = []
            if fingerprint.fingerprint_id not in self._by_ip[ip]:
                self._by_ip[ip].append(fingerprint.fingerprint_id)

    async def get_by_ip(self, ip_address: str) -> list[Fingerprint]:
        """Get all fingerprints for an IP."""
        ids = self._by_ip.get(ip_address, [])
        return [self._fingerprints[fid] for fid in ids if fid in self._fingerprints]

    async def get_recent(self, limit: int = 100) -> list[Fingerprint]:
        """Get recent fingerprints."""
        sorted_fps = sorted(
            self._fingerprints.values(),
            key=lambda f: f.created_at,
            reverse=True,
        )
        return sorted_fps[:limit]
