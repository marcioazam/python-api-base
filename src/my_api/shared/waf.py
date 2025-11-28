"""Web Application Firewall (WAF) - Security middleware with rule engine.

**Feature: api-architecture-analysis, Priority 11.1: WAF**
**Validates: Requirements 5.3, 5.5**

Provides:
- SQL injection detection
- XSS (Cross-Site Scripting) detection
- Path traversal detection
- Command injection detection
- Configurable rule engine
- Request blocking and logging
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable


class ThreatType(str, Enum):
    """Types of security threats detected."""

    SQL_INJECTION = "sql_injection"
    XSS = "xss"
    PATH_TRAVERSAL = "path_traversal"
    COMMAND_INJECTION = "command_injection"
    PROTOCOL_VIOLATION = "protocol_violation"
    MALFORMED_REQUEST = "malformed_request"
    RATE_ABUSE = "rate_abuse"
    BOT_DETECTION = "bot_detection"
    CUSTOM = "custom"


class RuleAction(str, Enum):
    """Action to take when rule matches."""

    BLOCK = "block"
    LOG = "log"
    CHALLENGE = "challenge"
    ALLOW = "allow"


class RuleSeverity(str, Enum):
    """Severity level of a rule."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


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
            except re.error:
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
    timestamp: datetime = field(default_factory=datetime.now)

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


# Default SQL Injection patterns
SQL_INJECTION_PATTERNS = [
    r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER)\b.*\b(FROM|INTO|SET|TABLE)\b)",
    r"(\bOR\b\s+\d+\s*=\s*\d+)",
    r"(\bAND\b\s+\d+\s*=\s*\d+)",
    r"(--\s*$|;\s*--)",
    r"(\b(EXEC|EXECUTE)\s*\()",
    r"(\/\*.*\*\/)",
    r"(\bWAITFOR\b\s+\bDELAY\b)",
    r"(\bBENCHMARK\b\s*\()",
    r"(\bSLEEP\b\s*\()",
    r"('.*\bOR\b.*')",
]

# Default XSS patterns
XSS_PATTERNS = [
    r"(<script[^>]*>.*?</script>)",
    r"(javascript\s*:)",
    r"(on\w+\s*=)",
    r"(<iframe[^>]*>)",
    r"(<object[^>]*>)",
    r"(<embed[^>]*>)",
    r"(<svg[^>]*onload)",
    r"(expression\s*\()",
    r"(vbscript\s*:)",
    r"(<img[^>]+onerror)",
]

# Default Path Traversal patterns
PATH_TRAVERSAL_PATTERNS = [
    r"(\.\.\/)",
    r"(\.\.\\)",
    r"(%2e%2e%2f)",
    r"(%2e%2e\/)",
    r"(\.\.%2f)",
    r"(%2e%2e%5c)",
    r"(\/etc\/passwd)",
    r"(\/etc\/shadow)",
    r"(c:\\windows)",
    r"(%00)",
]

# Default Command Injection patterns
COMMAND_INJECTION_PATTERNS = [
    r"(;\s*\w+)",
    r"(\|\s*\w+)",
    r"(`[^`]+`)",
    r"(\$\([^)]+\))",
    r"(\b(cat|ls|dir|type|echo|wget|curl)\b)",
    r"(>\s*\/)",
    r"(<\s*\/)",
    r"(\b(rm|del|rmdir)\b\s+-)",
]


class WAFRuleEngine:
    """Rule engine for WAF."""

    def __init__(self) -> None:
        """Initialize rule engine."""
        self._rules: dict[str, WAFRule] = {}
        self._custom_validators: list[Callable[[WAFRequest], ThreatDetection | None]] = []

    def add_rule(self, rule: WAFRule) -> "WAFRuleEngine":
        """Add a rule to the engine."""
        self._rules[rule.id] = rule
        return self

    def remove_rule(self, rule_id: str) -> bool:
        """Remove a rule by ID."""
        if rule_id in self._rules:
            del self._rules[rule_id]
            return True
        return False

    def get_rule(self, rule_id: str) -> WAFRule | None:
        """Get a rule by ID."""
        return self._rules.get(rule_id)

    def enable_rule(self, rule_id: str) -> bool:
        """Enable a rule."""
        rule = self._rules.get(rule_id)
        if rule:
            rule.enabled = True
            return True
        return False

    def disable_rule(self, rule_id: str) -> bool:
        """Disable a rule."""
        rule = self._rules.get(rule_id)
        if rule:
            rule.enabled = False
            return True
        return False

    def add_custom_validator(
        self,
        validator: Callable[[WAFRequest], ThreatDetection | None],
    ) -> "WAFRuleEngine":
        """Add custom validation function."""
        self._custom_validators.append(validator)
        return self

    def _check_value(
        self,
        value: str,
        target: str,
    ) -> list[ThreatDetection]:
        """Check a value against all rules."""
        detections: list[ThreatDetection] = []
        for rule in self._rules.values():
            if not rule.enabled:
                continue
            if target not in rule.targets:
                continue
            if rule.matches(value):
                detections.append(
                    ThreatDetection(
                        detected=True,
                        rule=rule,
                        matched_value=value[:100],  # Truncate for safety
                        target=target,
                    )
                )
        return detections

    def inspect(self, request: WAFRequest) -> list[ThreatDetection]:
        """Inspect request against all rules."""
        all_detections: list[ThreatDetection] = []

        # Check query parameters
        for key, value in request.query_params.items():
            all_detections.extend(self._check_value(f"{key}={value}", "query"))

        # Check headers
        for key, value in request.headers.items():
            all_detections.extend(self._check_value(f"{key}: {value}", "headers"))

        # Check body
        if request.body:
            all_detections.extend(self._check_value(request.body, "body"))

        # Check path
        all_detections.extend(self._check_value(request.path, "path"))

        # Run custom validators
        for validator in self._custom_validators:
            result = validator(request)
            if result and result.detected:
                all_detections.append(result)

        return all_detections

    def list_rules(self) -> list[WAFRule]:
        """List all rules."""
        return list(self._rules.values())

    def get_enabled_rules(self) -> list[WAFRule]:
        """Get only enabled rules."""
        return [r for r in self._rules.values() if r.enabled]


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

        # Load default rules
        self._load_default_rules()

    def _load_default_rules(self) -> None:
        """Load default security rules."""
        # SQL Injection rules
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

        # XSS rules
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

        # Path Traversal rules
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

        # Command Injection rules
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
        import time

        start_time = time.time()

        # Check if disabled or whitelisted
        if not self._enabled:
            return WAFResponse(allowed=True)

        if request.client_ip and self.is_whitelisted(request.client_ip):
            return WAFResponse(allowed=True)

        # Run inspection
        detections = self._engine.inspect(request)

        # Log detections
        if self._log_detections and detections:
            self._log_detection(detections)

        # Determine if blocked
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
        # Trim log if too large
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

        # Count by threat type
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
