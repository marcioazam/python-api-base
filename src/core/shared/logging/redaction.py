"""PII redaction processor for structured logs.

Automatically detects and redacts personally identifiable information (PII)
from log entries before they are emitted or stored.

Supports:
- Email addresses
- Passwords
- Credit card numbers
- SSN/CPF
- Phone numbers
- IP addresses (optional)

**Feature: observability-infrastructure**
**Requirement: R1 - Structured Logging Infrastructure (AC5: PII redaction)**

Example:
    >>> processor = RedactionProcessor()
    >>> event = {"event": "User admin@example.com logged in"}
    >>> result = processor(None, None, event)
    >>> "ad***@example.com" in result["event"]
    True
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, ClassVar


@dataclass
class PIIPattern:
    """Pattern for detecting and redacting PII."""

    name: str
    pattern: re.Pattern[str]
    replacement: str | None = None
    mask_func: Any = None

    def redact(self, text: str) -> str:
        """Redact matches in text."""
        if self.mask_func:
            return self.pattern.sub(self.mask_func, text)
        if self.replacement:
            return self.pattern.sub(self.replacement, text)
        return text


def _mask_email(match: re.Match[str]) -> str:
    """Mask email address, keeping first 2 chars and domain."""
    email = match.group(0)
    parts = email.split("@")
    if len(parts) == 2:
        local = parts[0]
        domain = parts[1]
        masked_local = local[:2] + "***" if len(local) > 2 else "***"
        return f"{masked_local}@{domain}"
    return "***@***.***"


def _mask_credit_card(match: re.Match[str]) -> str:
    """Mask credit card, keeping last 4 digits."""
    cc = re.sub(r"[\s-]", "", match.group(0))
    if len(cc) >= 4:
        return f"****-****-****-{cc[-4:]}"
    return "****-****-****-****"


def _mask_phone(match: re.Match[str]) -> str:
    """Mask phone number, keeping last 4 digits."""
    phone = re.sub(r"[^\d]", "", match.group(0))
    if len(phone) >= 4:
        return f"***-***-{phone[-4:]}"
    return "***-***-****"


def _mask_ssn_cpf(match: re.Match[str]) -> str:
    """Mask SSN/CPF completely."""
    return "***-**-****"


# Default PII patterns
PII_PATTERNS: dict[str, PIIPattern] = {
    "email": PIIPattern(
        name="email",
        pattern=re.compile(
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            re.IGNORECASE,
        ),
        mask_func=_mask_email,
    ),
    "password_json": PIIPattern(
        name="password_json",
        pattern=re.compile(
            r'(["\']password["\'])\s*:\s*["\'][^"\']*["\']',
            re.IGNORECASE,
        ),
        replacement=r'\1: "***"',
    ),
    "password_field": PIIPattern(
        name="password_field",
        pattern=re.compile(
            r"(password=)[^\s,\)]+",
            re.IGNORECASE,
        ),
        replacement=r"\1***",
    ),
    "credit_card": PIIPattern(
        name="credit_card",
        pattern=re.compile(
            r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",
        ),
        mask_func=_mask_credit_card,
    ),
    "ssn": PIIPattern(
        name="ssn",
        pattern=re.compile(
            r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b",
        ),
        mask_func=_mask_ssn_cpf,
    ),
    "cpf": PIIPattern(
        name="cpf",
        pattern=re.compile(
            r"\b\d{3}\.?\d{3}\.?\d{3}[-.]?\d{2}\b",
        ),
        mask_func=_mask_ssn_cpf,
    ),
    "phone": PIIPattern(
        name="phone",
        pattern=re.compile(
            r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
        ),
        mask_func=_mask_phone,
    ),
    "bearer_token": PIIPattern(
        name="bearer_token",
        pattern=re.compile(
            r"(Bearer\s+)[A-Za-z0-9\-_]+\.?[A-Za-z0-9\-_]*\.?[A-Za-z0-9\-_]*",
            re.IGNORECASE,
        ),
        replacement=r"\1***",
    ),
    "api_key": PIIPattern(
        name="api_key",
        pattern=re.compile(
            r'(["\']?(?:api[_-]?key|apikey|x-api-key)["\']?\s*[:=]\s*)["\']?[A-Za-z0-9\-_]{16,}["\']?',
            re.IGNORECASE,
        ),
        replacement=r"\1***",
    ),
}


@dataclass
class RedactionProcessor:
    """Structlog processor that redacts PII from log events.

    Attributes:
        patterns: Dictionary of PII patterns to apply
        fields_to_redact: Set of field names to completely redact
        enabled: Whether redaction is enabled

    Example:
        >>> processor = RedactionProcessor()
        >>> event = {"event": "Login: admin@example.com", "password": "secret"}
        >>> result = processor(None, None, event)
        >>> "***" in result["event"]
        True
        >>> result["password"]
        '***'
    """

    patterns: dict[str, PIIPattern] = field(default_factory=lambda: PII_PATTERNS.copy())
    fields_to_redact: set[str] = field(
        default_factory=lambda: {
            "password",
            "passwd",
            "secret",
            "token",
            "api_key",
            "apikey",
            "authorization",
            "auth",
            "credential",
            "credentials",
        }
    )
    enabled: bool = True

    # Fields that should never be redacted
    SAFE_FIELDS: ClassVar[set[str]] = {
        "timestamp",
        "@timestamp",
        "level",
        "log.level",
        "logger",
        "log.logger",
        "correlation_id",
        "trace.id",
        "service_name",
        "service.name",
        "environment",
        "ecs.version",
    }

    def __call__(
        self,
        logger: Any,
        method_name: str,
        event_dict: dict[str, Any],
    ) -> dict[str, Any]:
        """Process log event and redact PII.

        Args:
            logger: Logger instance (unused)
            method_name: Log method name (unused)
            event_dict: Log event dictionary

        Returns:
            Event dictionary with PII redacted
        """
        if not self.enabled:
            return event_dict

        return self._redact_dict(event_dict)

    def _redact_dict(self, data: dict[str, Any]) -> dict[str, Any]:
        """Recursively redact PII from dictionary."""
        result = {}

        for key, value in data.items():
            # Skip safe fields
            if key in self.SAFE_FIELDS:
                result[key] = value
                continue

            # Completely redact sensitive field names
            if key.lower() in self.fields_to_redact:
                result[key] = "***"
                continue

            # Recursively process nested structures
            if isinstance(value, dict):
                result[key] = self._redact_dict(value)
            elif isinstance(value, list):
                result[key] = self._redact_list(value)
            elif isinstance(value, str):
                result[key] = self._redact_string(value)
            else:
                result[key] = value

        return result

    def _redact_list(self, data: list[Any]) -> list[Any]:
        """Recursively redact PII from list."""
        result = []

        for item in data:
            if isinstance(item, dict):
                result.append(self._redact_dict(item))
            elif isinstance(item, list):
                result.append(self._redact_list(item))
            elif isinstance(item, str):
                result.append(self._redact_string(item))
            else:
                result.append(item)

        return result

    def _redact_string(self, text: str) -> str:
        """Apply all PII patterns to string."""
        for pattern in self.patterns.values():
            text = pattern.redact(text)
        return text

    def add_pattern(self, name: str, pattern: PIIPattern) -> None:
        """Add a custom PII pattern.

        Args:
            name: Pattern name
            pattern: PIIPattern instance

        Example:
            >>> processor = RedactionProcessor()
            >>> processor.add_pattern(
            ...     "custom_id",
            ...     PIIPattern(
            ...         name="custom_id",
            ...         pattern=re.compile(r"CUST-\\d{6}"),
            ...         replacement="CUST-******",
            ...     ),
            ... )
        """
        self.patterns[name] = pattern

    def remove_pattern(self, name: str) -> None:
        """Remove a PII pattern.

        Args:
            name: Pattern name to remove
        """
        self.patterns.pop(name, None)


def create_redaction_processor(
    enabled: bool = True,
    extra_patterns: dict[str, PIIPattern] | None = None,
    extra_fields: set[str] | None = None,
) -> RedactionProcessor:
    """Factory function to create a configured RedactionProcessor.

    Args:
        enabled: Whether redaction is enabled
        extra_patterns: Additional PII patterns to add
        extra_fields: Additional field names to completely redact

    Returns:
        Configured RedactionProcessor

    Example:
        >>> processor = create_redaction_processor(extra_fields={"custom_secret"})
    """
    processor = RedactionProcessor(enabled=enabled)

    if extra_patterns:
        for name, pattern in extra_patterns.items():
            processor.add_pattern(name, pattern)

    if extra_fields:
        processor.fields_to_redact.update(extra_fields)

    return processor
