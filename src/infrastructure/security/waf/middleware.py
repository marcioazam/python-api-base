"""WAF middleware for request inspection and blocking.

**Feature: file-size-compliance-phase2, Task 2.1**
**Validates: Requirements 1.1, 5.1, 5.2, 5.3**
"""

import time
from typing import Any

from .engine import WAFRuleEngine
from .enums import RuleAction, RuleSeverity, ThreatType
from .models import ThreatDetection, WAFRequest, WAFResponse, WAFRule
from .patterns import (
    COMMAND_INJECTION_PATTERNS,
    PATH_TRAVERSAL_PATTERNS,
    SQL_INJECTION_PATTERNS,
    XSS_PATTERNS,
)


class WAFMiddleware:
    """Web Application Firewall middleware."""

    def __init__(
        self,
        enabled: bool = True,
        block_on_detection: bool = True,
        log_detections: bool = True,
    ) -> None:
        """Initialize WAF middleware."""
        self._enabled = enabled
        self._block_on_detection = block_on_detection
        self._log_detections = log_detections
        self._engine = WAFRuleEngine()
        self._whitelist: set[str] = set()
        self._detection_log: list[ThreatDetection] = []
        self._max_log_size = 1000

        self._load_default_rules()

    def _load_default_rules(self) -> None:
        """Load default security rules."""
        for i, pattern in enumerate(SQL_INJECTION_PATTERNS):
            self._engine.add_rule(
                WAFRule(
                    id=f"sqli-{i+1}",
                    name=f"SQL Injection Pattern {i+1}",
                    threat_type=ThreatType.SQL_INJECTION,
                    pattern=pattern,
                    severity=RuleSeverity.CRITICAL,
                )
            )

        for i, pattern in enumerate(XSS_PATTERNS):
            self._engine.add_rule(
                WAFRule(
                    id=f"xss-{i+1}",
                    name=f"XSS Pattern {i+1}",
                    threat_type=ThreatType.XSS,
                    pattern=pattern,
                    severity=RuleSeverity.HIGH,
                )
            )

        for i, pattern in enumerate(PATH_TRAVERSAL_PATTERNS):
            self._engine.add_rule(
                WAFRule(
                    id=f"path-{i+1}",
                    name=f"Path Traversal Pattern {i+1}",
                    threat_type=ThreatType.PATH_TRAVERSAL,
                    pattern=pattern,
                    severity=RuleSeverity.HIGH,
                    targets=["body", "query", "headers", "path"],
                )
            )

        for i, pattern in enumerate(COMMAND_INJECTION_PATTERNS):
            self._engine.add_rule(
                WAFRule(
                    id=f"cmd-{i+1}",
                    name=f"Command Injection Pattern {i+1}",
                    threat_type=ThreatType.COMMAND_INJECTION,
                    pattern=pattern,
                    severity=RuleSeverity.CRITICAL,
                )
            )

    def add_to_whitelist(self, ip: str) -> None:
        """Add IP to whitelist."""
        self._whitelist.add(ip)

    def remove_from_whitelist(self, ip: str) -> None:
        """Remove IP from whitelist."""
        self._whitelist.discard(ip)

    def is_whitelisted(self, ip: str) -> bool:
        """Check if IP is whitelisted."""
        return ip in self._whitelist

    def inspect_request(self, request: WAFRequest) -> WAFResponse:
        """Inspect a request for threats."""
        start_time = time.time()

        if not self._enabled:
            return WAFResponse(allowed=True)

        if request.client_ip and self.is_whitelisted(request.client_ip):
            return WAFResponse(allowed=True)

        detections = self._engine.inspect(request)

        if self._log_detections and detections:
            self._log_detection(detections)

        blocked_by = None
        allowed = True

        if self._block_on_detection:
            for detection in detections:
                if detection.rule and detection.rule.action == RuleAction.BLOCK:
                    blocked_by = detection.rule
                    allowed = False
                    break

        inspection_time = (time.time() - start_time) * 1000

        return WAFResponse(
            allowed=allowed,
            detections=detections,
            blocked_by=blocked_by,
            inspection_time_ms=inspection_time,
        )

    def _log_detection(self, detections: list[ThreatDetection]) -> None:
        """Log threat detections."""
        self._detection_log.extend(detections)
        if len(self._detection_log) > self._max_log_size:
            self._detection_log = self._detection_log[-self._max_log_size:]

    def get_detection_log(
        self,
        threat_type: ThreatType | None = None,
        limit: int = 100,
    ) -> list[ThreatDetection]:
        """Get detection log, optionally filtered."""
        log = self._detection_log
        if threat_type:
            log = [d for d in log if d.threat_type == threat_type]
        return log[-limit:]

    def clear_detection_log(self) -> None:
        """Clear detection log."""
        self._detection_log.clear()

    def add_custom_rule(self, rule: WAFRule) -> None:
        """Add a custom rule."""
        self._engine.add_rule(rule)

    def get_stats(self) -> dict[str, Any]:
        """Get WAF statistics."""
        total_rules = len(self._engine.list_rules())
        enabled_rules = len(self._engine.get_enabled_rules())
        total_detections = len(self._detection_log)

        by_type: dict[str, int] = {}
        for detection in self._detection_log:
            if detection.threat_type:
                key = detection.threat_type.value
                by_type[key] = by_type.get(key, 0) + 1

        return {
            "enabled": self._enabled,
            "total_rules": total_rules,
            "enabled_rules": enabled_rules,
            "total_detections": total_detections,
            "detections_by_type": by_type,
            "whitelist_size": len(self._whitelist),
        }

    @property
    def engine(self) -> WAFRuleEngine:
        """Get the rule engine."""
        return self._engine


def create_waf_middleware(
    enabled: bool = True,
    block_on_detection: bool = True,
) -> WAFMiddleware:
    """Factory function to create WAF middleware."""
    return WAFMiddleware(
        enabled=enabled,
        block_on_detection=block_on_detection,
    )
