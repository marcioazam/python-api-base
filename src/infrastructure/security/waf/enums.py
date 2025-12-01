"""WAF enums for threat types, actions, and severity levels.

**Feature: file-size-compliance-phase2, Task 2.1**
**Validates: Requirements 1.1, 5.1, 5.2, 5.3**
"""

from enum import Enum


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
