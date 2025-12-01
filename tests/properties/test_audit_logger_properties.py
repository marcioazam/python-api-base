"""Property-based tests for security audit logging.

**Feature: code-review-refactoring, Task 13.3: Write property test for audit log completeness**
**Validates: Requirements 10.3, 10.4**
"""

import logging
from datetime import datetime, timezone

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from my_app.core.security.audit_logger import (
    SecurityAuditLogger,
    SecurityEvent,
    SecurityEventType,
    get_audit_logger,
)


# =============================================================================
# Strategies
# =============================================================================

@st.composite
def ip_address_strategy(draw: st.DrawFn) -> str:
    """Generate valid IPv4 addresses."""
    octets = [draw(st.integers(min_value=0, max_value=255)) for _ in range(4)]
    return ".".join(str(o) for o in octets)


@st.composite
def user_id_strategy(draw: st.DrawFn) -> str:
    """Generate valid user IDs."""
    return draw(st.text(
        min_size=1,
        max_size=50,
        alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="_-"),
    ).filter(lambda x: x.strip() != ""))


@st.composite
def resource_strategy(draw: st.DrawFn) -> str:
    """Generate valid resource paths."""
    segments = draw(st.lists(
        st.text(min_size=1, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz0123456789_-"),
        min_size=1,
        max_size=5,
    ))
    return "/" + "/".join(segments)


# =============================================================================
# Property Tests - Audit Log Completeness
# =============================================================================

class TestAuditLogCompletenessProperties:
    """Property tests for audit log completeness.

    **Feature: code-review-refactoring, Property 14: Audit Log Completeness**
    **Validates: Requirements 10.4**
    """

    @given(
        user_id=user_id_strategy(),
        client_ip=ip_address_strategy(),
        method=st.sampled_from(["password", "oauth", "api_key", "mfa"]),
    )
    @settings(max_examples=100)
    def test_auth_success_contains_required_fields(
        self,
        user_id: str,
        client_ip: str,
        method: str,
    ) -> None:
        """Property: Auth success log contains all required fields.

        **Feature: code-review-refactoring, Property 14: Audit Log Completeness**
        **Validates: Requirements 10.4**
        """
        logger = SecurityAuditLogger(redact_pii=False)
        event = logger.log_auth_success(user_id, client_ip, method)

        assert event.event_type == SecurityEventType.AUTH_SUCCESS
        assert event.user_id == user_id
        assert event.client_ip == client_ip
        assert event.action == method
        assert event.timestamp is not None
        assert isinstance(event.timestamp, datetime)

    @given(
        client_ip=ip_address_strategy(),
        reason=st.text(min_size=1, max_size=100),
    )
    @settings(max_examples=100)
    def test_auth_failure_contains_required_fields(
        self,
        client_ip: str,
        reason: str,
    ) -> None:
        """Property: Auth failure log contains client_ip, reason, and timestamp.

        **Feature: code-review-refactoring, Property 14: Audit Log Completeness**
        **Validates: Requirements 10.4**
        """
        logger = SecurityAuditLogger(redact_pii=False)
        event = logger.log_auth_failure(client_ip, reason)

        assert event.event_type == SecurityEventType.AUTH_FAILURE
        assert event.client_ip == client_ip
        assert event.reason == reason
        assert event.timestamp is not None

    @given(
        user_id=user_id_strategy(),
        resource=resource_strategy(),
        action=st.sampled_from(["read", "write", "delete", "admin"]),
    )
    @settings(max_examples=100)
    def test_authz_denied_contains_required_fields(
        self,
        user_id: str,
        resource: str,
        action: str,
    ) -> None:
        """Property: Authorization denied log contains user_id, resource, and action.

        **Feature: code-review-refactoring, Property 14: Audit Log Completeness**
        **Validates: Requirements 10.4**
        """
        logger = SecurityAuditLogger(redact_pii=False)
        event = logger.log_authorization_denied(user_id, resource, action)

        assert event.event_type == SecurityEventType.AUTHZ_DENIED
        assert event.user_id == user_id
        assert event.resource == resource
        assert event.action == action
        assert event.timestamp is not None

    @given(
        client_ip=ip_address_strategy(),
        endpoint=resource_strategy(),
        limit=st.text(min_size=1, max_size=50),
    )
    @settings(max_examples=100)
    def test_rate_limit_exceeded_contains_required_fields(
        self,
        client_ip: str,
        endpoint: str,
        limit: str,
    ) -> None:
        """Property: Rate limit exceeded log contains client_ip, endpoint, and limit.

        **Feature: code-review-refactoring, Property 14: Audit Log Completeness**
        **Validates: Requirements 10.4**
        """
        logger = SecurityAuditLogger(redact_pii=False)
        event = logger.log_rate_limit_exceeded(client_ip, endpoint, limit)

        assert event.event_type == SecurityEventType.RATE_LIMIT_EXCEEDED
        assert event.client_ip == client_ip
        assert event.resource == endpoint
        assert limit in event.reason
        assert event.timestamp is not None


# =============================================================================
# Property Tests - Secret Access Logging
# =============================================================================

class TestSecretAccessLoggingProperties:
    """Property tests for secret access logging.

    **Feature: code-review-refactoring, Property 15: Secret Access Logging**
    **Validates: Requirements 10.3**
    """

    @given(
        secret_name=st.text(min_size=1, max_size=50, alphabet="abcdefghijklmnopqrstuvwxyz0123456789_-"),
        accessor=user_id_strategy(),
        action=st.sampled_from(["read", "rotate", "delete", "create"]),
    )
    @settings(max_examples=100)
    def test_secret_access_logged_without_value(
        self,
        secret_name: str,
        accessor: str,
        action: str,
    ) -> None:
        """Property: Secret access is logged without exposing the secret value.

        **Feature: code-review-refactoring, Property 15: Secret Access Logging**
        **Validates: Requirements 10.3**
        """
        logger = SecurityAuditLogger(redact_pii=False)
        event = logger.log_secret_access(secret_name, accessor, action)

        assert event.event_type == SecurityEventType.SECRET_ACCESS
        assert event.resource == secret_name
        assert event.user_id == accessor
        assert event.action == action
        assert event.timestamp is not None

        # Verify no secret value in event
        event_dict = event.to_dict()
        assert "value" not in event_dict
        assert "secret_value" not in event_dict

    @given(
        secret_name=st.text(min_size=1, max_size=50),
        accessor=user_id_strategy(),
    )
    @settings(max_examples=100)
    def test_secret_access_event_serializable(
        self,
        secret_name: str,
        accessor: str,
    ) -> None:
        """Property: Secret access event is serializable to dict.

        **Feature: code-review-refactoring, Property 15: Secret Access Logging**
        **Validates: Requirements 10.3**
        """
        logger = SecurityAuditLogger(redact_pii=False)
        event = logger.log_secret_access(secret_name, accessor)

        event_dict = event.to_dict()

        assert isinstance(event_dict, dict)
        assert "event_type" in event_dict
        assert "timestamp" in event_dict
        assert "resource" in event_dict
        assert "user_id" in event_dict


# =============================================================================
# Property Tests - PII Redaction
# =============================================================================

class TestPIIRedactionProperties:
    """Property tests for PII redaction in logs."""

    @given(st.emails())
    @settings(max_examples=100)
    def test_email_addresses_are_redacted(self, email: str) -> None:
        """Property: Email addresses are redacted from log messages.

        **Feature: code-review-refactoring, Task 13.2: Implement log sanitization**
        **Validates: Requirements 7.6**
        """
        logger = SecurityAuditLogger(redact_pii=True)
        event = logger.log_auth_failure(
            client_ip="127.0.0.1",
            reason=f"Invalid credentials for {email}",
            attempted_user=email,
        )

        # Email should be redacted
        assert email not in (event.user_id or "")
        assert email not in (event.reason or "")

    @given(st.from_regex(r"\d{3}-\d{3}-\d{4}", fullmatch=True))
    @settings(max_examples=50)
    def test_phone_numbers_are_redacted(self, phone: str) -> None:
        """Property: Phone numbers are redacted from log messages.

        **Feature: code-review-refactoring, Task 13.2: Implement log sanitization**
        **Validates: Requirements 7.6**
        """
        logger = SecurityAuditLogger(redact_pii=True)
        event = logger.log_suspicious_activity(
            client_ip="127.0.0.1",
            description=f"Suspicious activity from phone {phone}",
        )

        assert phone not in (event.reason or "")

    def test_password_patterns_are_redacted(self) -> None:
        """Property: Password patterns are redacted from log messages.

        **Feature: code-review-refactoring, Task 13.2: Implement log sanitization**
        **Validates: Requirements 7.6**
        """
        logger = SecurityAuditLogger(redact_pii=True)
        event = logger.log_auth_failure(
            client_ip="127.0.0.1",
            reason="password=secret123 was incorrect",
        )

        assert "secret123" not in (event.reason or "")
        assert "[REDACTED]" in (event.reason or "")


# =============================================================================
# Property Tests - Event Serialization
# =============================================================================

class TestEventSerializationProperties:
    """Property tests for security event serialization."""

    @given(
        event_type=st.sampled_from(list(SecurityEventType)),
        client_ip=ip_address_strategy(),
        user_id=st.one_of(st.none(), user_id_strategy()),
        resource=st.one_of(st.none(), resource_strategy()),
    )
    @settings(max_examples=100)
    def test_event_to_dict_round_trip(
        self,
        event_type: SecurityEventType,
        client_ip: str,
        user_id: str | None,
        resource: str | None,
    ) -> None:
        """Property: Event serialization preserves all fields.

        **Feature: code-review-refactoring, Property 14: Audit Log Completeness**
        **Validates: Requirements 10.4**
        """
        event = SecurityEvent(
            event_type=event_type,
            timestamp=datetime.now(timezone.utc),
            client_ip=client_ip,
            user_id=user_id,
            resource=resource,
        )

        event_dict = event.to_dict()

        assert event_dict["event_type"] == event_type.value
        assert event_dict["client_ip"] == client_ip
        assert event_dict["user_id"] == user_id
        assert event_dict["resource"] == resource
        assert "timestamp" in event_dict

    @given(
        user_id=user_id_strategy(),
        client_ip=ip_address_strategy(),
    )
    @settings(max_examples=100)
    def test_all_event_types_have_timestamp(
        self,
        user_id: str,
        client_ip: str,
    ) -> None:
        """Property: All event types include timestamp.

        **Feature: code-review-refactoring, Property 14: Audit Log Completeness**
        **Validates: Requirements 10.4**
        """
        logger = SecurityAuditLogger(redact_pii=False)

        events = [
            logger.log_auth_success(user_id, client_ip, "password"),
            logger.log_auth_failure(client_ip, "invalid"),
            logger.log_authorization_denied(user_id, "/resource", "read"),
            logger.log_rate_limit_exceeded(client_ip, "/api", "100/min"),
            logger.log_secret_access("secret", user_id),
            logger.log_token_revoked(user_id, "jti-123"),
            logger.log_suspicious_activity(client_ip, "suspicious"),
        ]

        for event in events:
            assert event.timestamp is not None
            assert isinstance(event.timestamp, datetime)
            assert event.timestamp.tzinfo is not None


# =============================================================================
# Property Tests - Singleton Pattern
# =============================================================================

class TestSingletonProperties:
    """Property tests for audit logger singleton."""

    def test_get_audit_logger_returns_same_instance(self) -> None:
        """Property: get_audit_logger returns the same instance."""
        logger1 = get_audit_logger()
        logger2 = get_audit_logger()

        assert logger1 is logger2

    def test_audit_logger_is_functional(self) -> None:
        """Property: Global audit logger is functional."""
        logger = get_audit_logger()

        event = logger.log_auth_success("test-user", "127.0.0.1", "test")

        assert event.event_type == SecurityEventType.AUTH_SUCCESS
        assert event.user_id == "test-user"
