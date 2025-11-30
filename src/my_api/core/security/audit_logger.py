"""Security audit logging for authentication and authorization events.

**Feature: code-review-refactoring, Task 13.1: Create SecurityAuditLogger**
**Validates: Requirements 10.4, 10.5**

Provides structured logging for security-relevant events including:
- Authentication success/failure
- Authorization denials
- Rate limit exceeded events
- Secret access events
"""

import logging
import re
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from typing import Any

from my_api.shared.utils.ids import generate_ulid


class SecurityEventType(str, Enum):
    """Types of security events."""

    AUTH_SUCCESS = "AUTH_SUCCESS"
    AUTH_FAILURE = "AUTH_FAILURE"
    AUTHZ_DENIED = "AUTHZ_DENIED"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    SECRET_ACCESS = "SECRET_ACCESS"
    TOKEN_REVOKED = "TOKEN_REVOKED"
    SUSPICIOUS_ACTIVITY = "SUSPICIOUS_ACTIVITY"


@dataclass(frozen=True, slots=True)
class SecurityEvent:
    """Immutable security event record with correlation ID.
    
    **Feature: core-improvements-v2**
    **Validates: Requirements 4.5**
    """

    event_type: SecurityEventType
    timestamp: datetime
    correlation_id: str
    client_ip: str | None = None
    user_id: str | None = None
    resource: str | None = None
    action: str | None = None
    reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary for logging."""
        return {
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id,
            "client_ip": self.client_ip,
            "user_id": self.user_id,
            "resource": self.resource,
            "action": self.action,
            "reason": self.reason,
            **self.metadata,
        }


class SecurityAuditLogger:
    """Log security-relevant events for audit trail.

    **Feature: code-review-refactoring, Property 14: Audit Log Completeness**
    **Validates: Requirements 10.4, 10.5**
    """

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

    def __init__(
        self,
        logger: logging.Logger | None = None,
        redact_pii: bool = True,
        correlation_id_provider: Callable[[], str] | None = None,
        redact_ip_addresses: bool = False,
    ) -> None:
        """Initialize security audit logger.

        Args:
            logger: Logger instance to use. Defaults to security logger.
            redact_pii: Whether to redact PII from log messages.
            correlation_id_provider: Callable to get correlation ID. Defaults to generate_ulid.
            redact_ip_addresses: Whether to redact IP addresses.
            
        **Feature: core-improvements-v2**
        **Validates: Requirements 4.1, 4.3, 5.1**
        """
        self._logger = logger or logging.getLogger("security.audit")
        self._redact_pii = redact_pii
        self._get_correlation_id = correlation_id_provider or generate_ulid
        self._redact_ip = redact_ip_addresses

    def _redact(self, value: str | None) -> str | None:
        """Redact PII from a string value.
        
        **Feature: core-improvements-v2**
        **Validates: Requirements 5.2, 5.3, 5.4, 5.5**
        """
        if not value or not self._redact_pii:
            return value

        result = value
        for pattern, replacement in self.PII_PATTERNS:
            result = pattern.sub(replacement, result)

        # Apply IP redaction if enabled
        if self._redact_ip:
            for pattern, replacement in self.IP_PATTERNS:
                result = pattern.sub(replacement, result)

        return result

    def _create_event(
        self,
        event_type: SecurityEventType,
        **kwargs: Any,
    ) -> SecurityEvent:
        """Create a security event with current timestamp and correlation ID.
        
        **Feature: core-improvements-v2**
        **Validates: Requirements 4.2, 4.4**
        """
        return SecurityEvent(
            event_type=event_type,
            timestamp=datetime.now(UTC),
            correlation_id=self._get_correlation_id(),
            **kwargs,
        )

    def log_auth_success(
        self,
        user_id: str,
        client_ip: str,
        method: str,
        metadata: dict[str, Any] | None = None,
    ) -> SecurityEvent:
        """Log successful authentication.

        Args:
            user_id: Authenticated user ID.
            client_ip: Client IP address.
            method: Authentication method (password, oauth, api_key).
            metadata: Additional metadata.

        Returns:
            The logged security event.
        """
        event = self._create_event(
            SecurityEventType.AUTH_SUCCESS,
            user_id=user_id,
            client_ip=client_ip,
            action=method,
            metadata=metadata or {},
        )

        self._logger.info(
            "Authentication successful",
            extra=event.to_dict(),
        )
        return event

    def log_auth_failure(
        self,
        client_ip: str,
        reason: str,
        attempted_user: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SecurityEvent:
        """Log failed authentication attempt.

        Args:
            client_ip: Client IP address.
            reason: Failure reason.
            attempted_user: Username/email attempted (will be redacted).
            metadata: Additional metadata.

        Returns:
            The logged security event.
        """
        event = self._create_event(
            SecurityEventType.AUTH_FAILURE,
            client_ip=client_ip,
            reason=self._redact(reason),
            user_id=self._redact(attempted_user),
            metadata=metadata or {},
        )

        self._logger.warning(
            "Authentication failed",
            extra=event.to_dict(),
        )
        return event

    def log_authorization_denied(
        self,
        user_id: str,
        resource: str,
        action: str,
        reason: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SecurityEvent:
        """Log authorization denial.

        Args:
            user_id: User ID attempting access.
            resource: Resource being accessed.
            action: Action attempted.
            reason: Denial reason.
            metadata: Additional metadata.

        Returns:
            The logged security event.
        """
        event = self._create_event(
            SecurityEventType.AUTHZ_DENIED,
            user_id=user_id,
            resource=resource,
            action=action,
            reason=reason,
            metadata=metadata or {},
        )

        self._logger.warning(
            "Authorization denied",
            extra=event.to_dict(),
        )
        return event

    def log_rate_limit_exceeded(
        self,
        client_ip: str,
        endpoint: str,
        limit: str,
        user_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SecurityEvent:
        """Log rate limit exceeded event.

        Args:
            client_ip: Client IP address.
            endpoint: Endpoint that was rate limited.
            limit: Rate limit that was exceeded.
            user_id: User ID if authenticated.
            metadata: Additional metadata.

        Returns:
            The logged security event.
        """
        event = self._create_event(
            SecurityEventType.RATE_LIMIT_EXCEEDED,
            client_ip=client_ip,
            resource=endpoint,
            reason=f"Rate limit exceeded: {limit}",
            user_id=user_id,
            metadata=metadata or {},
        )

        self._logger.warning(
            "Rate limit exceeded",
            extra=event.to_dict(),
        )
        return event

    def log_secret_access(
        self,
        secret_name: str,
        accessor: str,
        action: str = "read",
        metadata: dict[str, Any] | None = None,
    ) -> SecurityEvent:
        """Log secret access without exposing the secret value.

        **Feature: code-review-refactoring, Property 15: Secret Access Logging**
        **Validates: Requirements 10.3**

        Args:
            secret_name: Name/identifier of the secret.
            accessor: Who/what accessed the secret.
            action: Action performed (read, rotate, delete).
            metadata: Additional metadata.

        Returns:
            The logged security event.
        """
        event = self._create_event(
            SecurityEventType.SECRET_ACCESS,
            resource=secret_name,
            user_id=accessor,
            action=action,
            metadata=metadata or {},
        )

        self._logger.info(
            "Secret accessed",
            extra=event.to_dict(),
        )
        return event

    def log_token_revoked(
        self,
        user_id: str,
        token_jti: str,
        reason: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SecurityEvent:
        """Log token revocation.

        Args:
            user_id: User whose token was revoked.
            token_jti: Token ID (JTI claim).
            reason: Revocation reason.
            metadata: Additional metadata.

        Returns:
            The logged security event.
        """
        event = self._create_event(
            SecurityEventType.TOKEN_REVOKED,
            user_id=user_id,
            resource=token_jti,
            reason=reason,
            metadata=metadata or {},
        )

        self._logger.info(
            "Token revoked",
            extra=event.to_dict(),
        )
        return event

    def log_suspicious_activity(
        self,
        client_ip: str,
        description: str,
        user_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SecurityEvent:
        """Log suspicious activity detection.

        Args:
            client_ip: Client IP address.
            description: Description of suspicious activity.
            user_id: User ID if known.
            metadata: Additional metadata.

        Returns:
            The logged security event.
        """
        event = self._create_event(
            SecurityEventType.SUSPICIOUS_ACTIVITY,
            client_ip=client_ip,
            reason=self._redact(description),
            user_id=user_id,
            metadata=metadata or {},
        )

        self._logger.error(
            "Suspicious activity detected",
            extra=event.to_dict(),
        )
        return event


# Module-level singleton with thread-safe initialization
_audit_logger: SecurityAuditLogger | None = None
_audit_lock = threading.Lock()


def get_audit_logger() -> SecurityAuditLogger:
    """Get the global security audit logger instance (thread-safe).
    
    Uses double-check locking pattern for thread-safe lazy initialization.
    
    **Feature: core-improvements-v2**
    **Validates: Requirements 1.3, 1.4, 1.5**
    """
    global _audit_logger
    if _audit_logger is None:
        with _audit_lock:
            if _audit_logger is None:  # Double-check locking
                _audit_logger = SecurityAuditLogger()
    return _audit_logger
