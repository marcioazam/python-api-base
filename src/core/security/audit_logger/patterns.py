"""PII redaction patterns for security audit logging.

**Feature: full-codebase-review-2025, Task 1.4: Refactor audit_logger**
**Validates: Requirements 9.2**
"""

import re

# PII patterns for redaction
PII_PATTERNS = [
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"), "[EMAIL]"),
    (re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b"), "[PHONE]"),
    (re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"), "[PHONE]"),
    (re.compile(r"\b\+\d{1,3}[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}\b"), "[PHONE]"),
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[SSN]"),
    (re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b"), "[CARD]"),
    (re.compile(r"\b\d{16}\b"), "[CARD]"),
    (re.compile(r"password[\"']?\s*[:=]\s*[\"']?[^\"'\s]+", re.I), "password=[REDACTED]"),
    (re.compile(r"secret[\"']?\s*[:=]\s*[\"']?[^\"'\s]+", re.I), "secret=[REDACTED]"),
    (re.compile(r"token[\"']?\s*[:=]\s*[\"']?[^\"'\s]+", re.I), "token=[REDACTED]"),
    (re.compile(r"api[_-]?key[\"']?\s*[:=]\s*[\"']?[^\"'\s]+", re.I), "api_key=[REDACTED]"),
    (re.compile(r"Bearer\s+[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+", re.I), "Bearer [REDACTED]"),
]

# IP address patterns (optional, configurable)
IP_PATTERNS = [
    (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), "[IP_REDACTED]"),
    (re.compile(r"\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b"), "[IP_REDACTED]"),
]
