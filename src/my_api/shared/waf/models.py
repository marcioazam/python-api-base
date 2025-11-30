"""WAF data models for rules, requests, responses, and detections.

**Feature: file-size-compliance-phase2, Task 2.1**
**Validates: Requirements 1.1, 5.1, 5.2, 5.3**

**Feature: shared-modules-code-review-fixes, Task 5.2, 7.1**
**Validates: Requirements 4.1, 4.2, 5.3**
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, UTC

from .enums import RuleAction, RuleSeverity, ThreatType

_logger = logging.getLogger(__name__)


@dataclass
class WAFRule:
    """A single WAF rule definition."""

    id: str
    name: str
    threat_type: ThreatType
    pattern: str
    action: RuleAction = RuleAction.BLOCK
    severity: RuleSeverity = RuleSeverity.HIGH
    enabled: bool = True
    targets: list[str] = field(default_factory=lambda: ["body", "query", "headers"])
    description: str = ""
    _compiled: re.Pattern | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        """Compile regex pattern."""
        if self.pattern:
            try:
                self._compiled = re.compile(self.pattern, re.IGNORECASE)
            except re.error as e:
                _logger.warning(
                    "Failed to compile WAF pattern",
                    extra={"rule_id": self.id, "pattern": self.pattern, "error": str(e)},
                )
                self._compiled = None

    def matches(self, value: str) -> bool:
        """Check if value matches the rule pattern."""
        if not self.enabled or self._compiled is None:
            return False
        return bool(self._compiled.search(value))


@dataclass
class ThreatDetection:
    """Result of threat detection."""

    detected: bool
    rule: WAFRule | None = None
    matched_value: str | None = None
    target: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def threat_type(self) -> ThreatType | None:
        """Get threat type from matched rule."""
        return self.rule.threat_type if self.rule else None

    @property
    def severity(self) -> RuleSeverity | None:
        """Get severity from matched rule."""
        return self.rule.severity if self.rule else None


@dataclass
class WAFRequest:
    """Normalized request for WAF inspection."""

    method: str
    path: str
    query_params: dict[str, str] = field(default_factory=dict)
    headers: dict[str, str] = field(default_factory=dict)
    body: str | None = None
    client_ip: str | None = None
    user_agent: str | None = None


@dataclass
class WAFResponse:
    """Response from WAF inspection."""

    allowed: bool
    detections: list[ThreatDetection] = field(default_factory=list)
    blocked_by: WAFRule | None = None
    inspection_time_ms: float = 0.0

    @property
    def threat_count(self) -> int:
        """Count of detected threats."""
        return len([d for d in self.detections if d.detected])
