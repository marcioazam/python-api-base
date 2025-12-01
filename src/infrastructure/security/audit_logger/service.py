"""Security audit logger service.

**Feature: full-codebase-review-2025, Task 1.4: Refactor audit_logger**
**Validates: Requirements 9.2**
"""

import logging
import threading
from collections.abc import Callable
from datetime import datetime, UTC
from typing import Any

from core.shared.utils.ids import generate_ulid

from .enums import SecurityEventType
from .models import SecurityEvent
from .patterns import IP_PATTERNS, PII_PATTERNS


class SecurityAuditLogger:
    """Log security-relevant events for audit trail.

    **Feature: code-review-refactoring, Property 14: Audit Log Completeness**
    **Validates: Requirements 10.4, 10.5**
    """

    def __init__(
        self,
        logger: logging.Logger | None = None,
        redact_pii: bool = True,
        correlation_id_provider: Callable[[], str] | None = None,
        redact_ip_addresses: bool = False,
    ) -> None:
        """Initialize security audit logger."""
        self._logger = logger or logging.getLogger("security.audit")
        self._redact_pii = redact_pii
        self._get_correlation_id = correlation_id_provider or generate_ulid
        self._redact_ip = redact_ip_addresses

    def _redact(self, value: str | None) -> str | None:
        """Redact PII from a string value."""
        if not value or not self._redact_pii:
            return value
        result = value
        for pattern, replacement in PII_PATTERNS:
            result = pattern.sub(replacement, result)
        if self._redact_ip:
            for pattern, replacement in IP_PATTERNS:
                result = pattern.sub(replacement, result)
        return result

    def _create_event(
        self, event_type: SecurityEventType, **kwargs: Any
    ) -> SecurityEvent:
        """Create a security event with current timestamp and correlation ID."""
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
        """Log successful authentication."""
        event = self._create_event(
            SecurityEventType.AUTH_SUCCESS,
            user_id=user_id,
            client_ip=client_ip,
            action=method,
            metadata=metadata or {},
        )
        self._logger.info("Authentication successful", extra=event.to_dict())
        return event

    def log_auth_failure(
        self,
        client_ip: str,
        reason: str,
        attempted_user: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SecurityEvent:
        """Log failed authentication attempt."""
        event = self._create_event(
            SecurityEventType.AUTH_FAILURE,
            client_ip=client_ip,
            reason=self._redact(reason),
            user_id=self._redact(attempted_user),
            metadata=metadata or {},
        )
        self._logger.warning("Authentication failed", extra=event.to_dict())
        return event

    def log_authorization_denied(
        self,
        user_id: str,
        resource: str,
        action: str,
        reason: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SecurityEvent:
        """Log authorization denial."""
        event = self._create_event(
            SecurityEventType.AUTHZ_DENIED,
            user_id=user_id,
            resource=resource,
            action=action,
            reason=reason,
            metadata=metadata or {},
        )
        self._logger.warning("Authorization denied", extra=event.to_dict())
        return event

    def log_rate_limit_exceeded(
        self,
        client_ip: str,
        endpoint: str,
        limit: str,
        user_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SecurityEvent:
        """Log rate limit exceeded event."""
        event = self._create_event(
            SecurityEventType.RATE_LIMIT_EXCEEDED,
            client_ip=client_ip,
            resource=endpoint,
            reason=f"Rate limit exceeded: {limit}",
            user_id=user_id,
            metadata=metadata or {},
        )
        self._logger.warning("Rate limit exceeded", extra=event.to_dict())
        return event

    def log_secret_access(
        self,
        secret_name: str,
        accessor: str,
        action: str = "read",
        metadata: dict[str, Any] | None = None,
    ) -> SecurityEvent:
        """Log secret access without exposing the secret value."""
        event = self._create_event(
            SecurityEventType.SECRET_ACCESS,
            resource=secret_name,
            user_id=accessor,
            action=action,
            metadata=metadata or {},
        )
        self._logger.info("Secret accessed", extra=event.to_dict())
        return event

    def log_token_revoked(
        self,
        user_id: str,
        token_jti: str,
        reason: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SecurityEvent:
        """Log token revocation."""
        event = self._create_event(
            SecurityEventType.TOKEN_REVOKED,
            user_id=user_id,
            resource=token_jti,
            reason=reason,
            metadata=metadata or {},
        )
        self._logger.info("Token revoked", extra=event.to_dict())
        return event

    def log_suspicious_activity(
        self,
        client_ip: str,
        description: str,
        user_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SecurityEvent:
        """Log suspicious activity detection."""
        event = self._create_event(
            SecurityEventType.SUSPICIOUS_ACTIVITY,
            client_ip=client_ip,
            reason=self._redact(description),
            user_id=user_id,
            metadata=metadata or {},
        )
        self._logger.error("Suspicious activity detected", extra=event.to_dict())
        return event


# Module-level singleton with thread-safe initialization
_audit_logger: SecurityAuditLogger | None = None
_audit_lock = threading.Lock()


def get_audit_logger() -> SecurityAuditLogger:
    """Get the global security audit logger instance (thread-safe)."""
    global _audit_logger
    if _audit_logger is None:
        with _audit_lock:
            if _audit_logger is None:
                _audit_logger = SecurityAuditLogger()
    return _audit_logger
