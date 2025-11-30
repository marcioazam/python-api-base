"""Fingerprint data models.

**Feature: file-size-compliance-phase2, Task 2.6**
**Validates: Requirements 1.6, 5.1, 5.2, 5.3**
"""

from dataclasses import dataclass, field
from datetime import datetime

from .enums import FingerprintComponent, SuspicionLevel


@dataclass(frozen=True, slots=True)
class RequestData:
    """Data extracted from a request for fingerprinting."""

    ip_address: str
    user_agent: str = ""
    accept_language: str = ""
    accept_encoding: str = ""
    accept: str = ""
    headers: dict[str, str] = field(default_factory=dict)
    client_hints: dict[str, str] = field(default_factory=dict)


@dataclass
class Fingerprint:
    """A computed fingerprint for a client."""

    fingerprint_id: str
    components: dict[FingerprintComponent, str]
    hash_value: str
    created_at: datetime
    confidence: float = 1.0

    @property
    def short_id(self) -> str:
        """Get short version of fingerprint ID."""
        return self.fingerprint_id[:16]


@dataclass
class SuspicionIndicator:
    """An indicator of suspicious behavior."""

    name: str
    description: str
    severity: SuspicionLevel
    weight: float = 1.0


@dataclass
class SuspicionAnalysis:
    """Analysis of suspicious indicators for a fingerprint."""

    fingerprint: Fingerprint
    indicators: list[SuspicionIndicator]
    overall_level: SuspicionLevel
    score: float
    details: str = ""

    @property
    def is_suspicious(self) -> bool:
        """Check if analysis indicates suspicion."""
        return self.overall_level not in (SuspicionLevel.NONE, SuspicionLevel.LOW)


@dataclass
class FingerprintConfig:
    """Configuration for fingerprint generation."""

    components: set[FingerprintComponent] = field(
        default_factory=lambda: {
            FingerprintComponent.IP_ADDRESS,
            FingerprintComponent.USER_AGENT,
            FingerprintComponent.ACCEPT_LANGUAGE,
            FingerprintComponent.ACCEPT_ENCODING,
        }
    )
    hash_algorithm: str = "sha256"
    include_ip_in_hash: bool = True
    normalize_user_agent: bool = True
    suspicion_thresholds: dict[SuspicionLevel, float] = field(
        default_factory=lambda: {
            SuspicionLevel.LOW: 0.2,
            SuspicionLevel.MEDIUM: 0.4,
            SuspicionLevel.HIGH: 0.6,
            SuspicionLevel.CRITICAL: 0.8,
        }
    )
