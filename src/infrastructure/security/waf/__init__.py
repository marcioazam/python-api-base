"""Web Application Firewall (WAF) - Security middleware with rule engine.

**Feature: file-size-compliance-phase2, Task 2.1**
**Validates: Requirements 1.1, 5.1, 5.2, 5.3**

Provides:
- SQL injection detection
- XSS (Cross-Site Scripting) detection
- Path traversal detection
- Command injection detection
- Configurable rule engine
- Request blocking and logging
"""

from .engine import WAFRuleEngine
from .enums import RuleAction, RuleSeverity, ThreatType
from .middleware import WAFMiddleware, create_waf_middleware
from .models import ThreatDetection, WAFRequest, WAFResponse, WAFRule
from .patterns import (
    COMMAND_INJECTION_PATTERNS,
    PATH_TRAVERSAL_PATTERNS,
    SQL_INJECTION_PATTERNS,
    XSS_PATTERNS,
)

__all__ = [
    "COMMAND_INJECTION_PATTERNS",
    "PATH_TRAVERSAL_PATTERNS",
    "RuleAction",
    "RuleSeverity",
    "SQL_INJECTION_PATTERNS",
    "ThreatDetection",
    "ThreatType",
    "WAFMiddleware",
    "WAFRequest",
    "WAFResponse",
    "WAFRule",
    "WAFRuleEngine",
    "XSS_PATTERNS",
    "create_waf_middleware",
]
