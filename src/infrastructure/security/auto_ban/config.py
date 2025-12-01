"""Auto-ban configuration and builders.

**Feature: file-size-compliance-phase2, Task 2.3**
**Validates: Requirements 1.3, 5.1, 5.2, 5.3**
"""

from dataclasses import dataclass, field
from datetime import timedelta

from .enums import ViolationType
from .models import BanThreshold


@dataclass
class AutoBanConfig:
    """Configuration for the auto-ban system."""

    thresholds: list[BanThreshold] = field(default_factory=list)
    default_ban_duration: timedelta = field(default_factory=lambda: timedelta(hours=24))
    escalation_enabled: bool = True
    escalation_multiplier: float = 2.0
    max_ban_duration: timedelta = field(default_factory=lambda: timedelta(days=30))
    permanent_ban_after: int = 5
    allowlist: set[str] = field(default_factory=set)

    @classmethod
    def default(cls) -> "AutoBanConfig":
        """Create default configuration."""
        return cls(
            thresholds=[
                BanThreshold(
                    violation_type=ViolationType.RATE_LIMIT,
                    max_violations=10,
                    time_window=timedelta(minutes=5),
                    ban_duration=timedelta(hours=1),
                ),
                BanThreshold(
                    violation_type=ViolationType.AUTH_FAILURE,
                    max_violations=5,
                    time_window=timedelta(minutes=15),
                    ban_duration=timedelta(hours=2),
                ),
                BanThreshold(
                    violation_type=ViolationType.BRUTE_FORCE,
                    max_violations=3,
                    time_window=timedelta(minutes=5),
                    ban_duration=timedelta(hours=24),
                ),
                BanThreshold(
                    violation_type=ViolationType.SUSPICIOUS_ACTIVITY,
                    max_violations=5,
                    time_window=timedelta(hours=1),
                    ban_duration=timedelta(hours=12),
                ),
                BanThreshold(
                    violation_type=ViolationType.SPAM,
                    max_violations=3,
                    time_window=timedelta(minutes=10),
                    ban_duration=timedelta(hours=6),
                ),
                BanThreshold(
                    violation_type=ViolationType.ABUSE,
                    max_violations=2,
                    time_window=timedelta(hours=1),
                    ban_duration=timedelta(days=7),
                ),
            ]
        )


class AutoBanConfigBuilder:
    """Fluent builder for AutoBanConfig."""

    def __init__(self) -> None:
        self._thresholds: list[BanThreshold] = []
        self._default_ban_duration = timedelta(hours=24)
        self._escalation_enabled = True
        self._escalation_multiplier = 2.0
        self._max_ban_duration = timedelta(days=30)
        self._permanent_ban_after = 5
        self._allowlist: set[str] = set()

    def add_threshold(
        self,
        violation_type: ViolationType,
        max_violations: int,
        time_window: timedelta,
        ban_duration: timedelta | None = None,
        severity_multiplier: float = 1.0,
    ) -> "AutoBanConfigBuilder":
        """Add a threshold configuration."""
        self._thresholds.append(
            BanThreshold(
                violation_type=violation_type,
                max_violations=max_violations,
                time_window=time_window,
                ban_duration=ban_duration,
                severity_multiplier=severity_multiplier,
            )
        )
        return self

    def with_default_ban_duration(self, duration: timedelta) -> "AutoBanConfigBuilder":
        """Set default ban duration."""
        self._default_ban_duration = duration
        return self

    def with_escalation(
        self, enabled: bool = True, multiplier: float = 2.0
    ) -> "AutoBanConfigBuilder":
        """Configure escalation settings."""
        self._escalation_enabled = enabled
        self._escalation_multiplier = multiplier
        return self

    def with_max_ban_duration(self, duration: timedelta) -> "AutoBanConfigBuilder":
        """Set maximum ban duration."""
        self._max_ban_duration = duration
        return self

    def with_permanent_ban_after(self, count: int) -> "AutoBanConfigBuilder":
        """Set number of bans before permanent."""
        self._permanent_ban_after = count
        return self

    def with_allowlist(self, identifiers: set[str]) -> "AutoBanConfigBuilder":
        """Set allowlist of identifiers that cannot be banned."""
        self._allowlist = identifiers
        return self

    def add_to_allowlist(self, identifier: str) -> "AutoBanConfigBuilder":
        """Add identifier to allowlist."""
        self._allowlist.add(identifier)
        return self

    def build(self) -> AutoBanConfig:
        """Build the configuration."""
        return AutoBanConfig(
            thresholds=self._thresholds,
            default_ban_duration=self._default_ban_duration,
            escalation_enabled=self._escalation_enabled,
            escalation_multiplier=self._escalation_multiplier,
            max_ban_duration=self._max_ban_duration,
            permanent_ban_after=self._permanent_ban_after,
            allowlist=self._allowlist,
        )
