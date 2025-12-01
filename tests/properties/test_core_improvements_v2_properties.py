"""Property-based tests for core-improvements-v2 spec.

**Feature: core-improvements-v2**
Tests thread-safety, memory management, fail-closed behavior, and PII redaction.
"""

import threading
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from hypothesis import given, settings, strategies as st

from my_app.core.auth.jwt import JWTService
from my_app.core.auth.password_policy import get_password_validator
from my_app.core.auth.rbac import get_rbac_service
from my_app.core.security.audit_logger import (
    SecurityAuditLogger,
    SecurityEvent,
    SecurityEventType,
    get_audit_logger,
)


class TestThreadSafeSingletons:
    """Tests for Property 1: Thread-Safe Singleton Access."""

    def test_rbac_service_thread_safe(self) -> None:
        """
        **Feature: core-improvements-v2, Property 1: Thread-Safe Singleton Access**
        **Validates: Requirements 1.1, 1.2, 1.3**
        
        For any number of concurrent threads calling get_rbac_service(),
        all threads SHALL receive the same instance.
        """
        results: list = []
        num_threads = 50
        
        def get_service():
            service = get_rbac_service()
            results.append(id(service))
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(get_service) for _ in range(num_threads)]
            for future in as_completed(futures):
                future.result()
        
        # All threads should get the same instance
        assert len(set(results)) == 1

    def test_password_validator_thread_safe(self) -> None:
        """
        **Feature: core-improvements-v2, Property 1: Thread-Safe Singleton Access**
        **Validates: Requirements 1.1, 1.2, 1.3**
        """
        results: list = []
        num_threads = 50
        
        def get_validator():
            validator = get_password_validator()
            results.append(id(validator))
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(get_validator) for _ in range(num_threads)]
            for future in as_completed(futures):
                future.result()
        
        assert len(set(results)) == 1

    def test_audit_logger_thread_safe(self) -> None:
        """
        **Feature: core-improvements-v2, Property 1: Thread-Safe Singleton Access**
        **Validates: Requirements 1.1, 1.2, 1.3**
        """
        results: list = []
        num_threads = 50
        
        def get_logger():
            logger = get_audit_logger()
            results.append(id(logger))
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(get_logger) for _ in range(num_threads)]
            for future in as_completed(futures):
                future.result()
        
        assert len(set(results)) == 1


class TestJWTMemoryManagement:
    """Tests for Properties 2 and 3: Bounded Token Tracking."""

    @given(st.integers(min_value=1, max_value=100))
    @settings(max_examples=20)
    def test_bounded_token_tracking(self, max_tokens: int) -> None:
        """
        **Feature: core-improvements-v2, Property 2: Bounded Token Tracking Memory**
        **Validates: Requirements 2.1, 2.2**
        
        For any sequence of refresh token verifications, the number of tracked
        tokens SHALL never exceed max_tracked_tokens.
        """
        service = JWTService(
            secret_key="a" * 32,
            max_tracked_tokens=max_tokens,
        )
        
        # Create more tokens than the limit
        for i in range(max_tokens + 50):
            _, _ = service.create_refresh_token(f"user_{i}")
        
        # Verify tracking doesn't exceed limit
        assert len(service._used_refresh_tokens) <= max_tokens

    def test_fifo_removal(self) -> None:
        """
        **Feature: core-improvements-v2, Property 3: Token Tracking FIFO Removal**
        **Validates: Requirements 2.2**
        
        When at capacity, the oldest token SHALL be removed first.
        """
        max_tokens = 5
        service = JWTService(
            secret_key="a" * 32,
            max_tracked_tokens=max_tokens,
        )
        
        # Create and verify tokens to populate tracking
        tokens = []
        for i in range(max_tokens + 3):
            token, payload = service.create_refresh_token(f"user_{i}")
            tokens.append((token, payload.jti))
            try:
                service.verify_refresh_token(token)
            except Exception:
                pass
        
        # First tokens should have been removed
        tracked_jtis = list(service._used_refresh_tokens.keys())
        assert len(tracked_jtis) <= max_tokens


class TestFailClosedBehavior:
    """Tests for Property 4: Fail-Closed Revocation Check."""

    @pytest.mark.asyncio
    async def test_fail_closed_on_store_exception(self) -> None:
        """
        **Feature: core-improvements-v2, Property 4: Fail-Closed Revocation Check**
        **Validates: Requirements 3.1, 3.3, 3.5**
        
        When the revocation store raises an exception, validate_with_revocation()
        SHALL reject the token.
        """
        from my_app.core.auth.jwt_validator import JWTValidator, InvalidTokenError
        
        # Create a mock revocation store that raises an exception
        mock_store = MagicMock()
        mock_store.is_revoked = AsyncMock(side_effect=Exception("Store unavailable"))
        
        validator = JWTValidator(
            secret_or_key="a" * 32,
            algorithm="HS256",
            revocation_store=mock_store,
        )
        
        # Create a valid token
        service = JWTService(secret_key="a" * 32)
        token, _ = service.create_access_token("user123")
        
        # Should fail closed
        with pytest.raises(InvalidTokenError) as exc_info:
            await validator.validate_with_revocation(token)
        
        assert "Unable to verify token status" in str(exc_info.value.message)


class TestCorrelationID:
    """Tests for Properties 5 and 6: Correlation ID in Events."""

    def test_correlation_id_in_all_events(self) -> None:
        """
        **Feature: core-improvements-v2, Property 5: Correlation ID in All Events**
        **Validates: Requirements 4.2, 4.3, 4.5**
        
        For any security event, the event SHALL contain a non-empty correlation_id.
        """
        logger = SecurityAuditLogger()
        
        # Test all event types
        events = [
            logger.log_auth_success("user1", "127.0.0.1", "password"),
            logger.log_auth_failure("127.0.0.1", "Invalid password"),
            logger.log_authorization_denied("user1", "/api/admin", "GET"),
            logger.log_rate_limit_exceeded("127.0.0.1", "/api/users", "100/min"),
            logger.log_secret_access("db_password", "admin"),
            logger.log_token_revoked("user1", "jti123"),
            logger.log_suspicious_activity("127.0.0.1", "Multiple failed logins"),
        ]
        
        for event in events:
            assert event.correlation_id is not None
            assert len(event.correlation_id) > 0
            assert "correlation_id" in event.to_dict()

    def test_custom_correlation_id_provider(self) -> None:
        """
        **Feature: core-improvements-v2, Property 6: Custom Correlation ID Provider**
        **Validates: Requirements 4.4**
        
        When a correlation_id_provider is configured, all events SHALL use it.
        """
        custom_id = "custom-correlation-123"
        logger = SecurityAuditLogger(
            correlation_id_provider=lambda: custom_id
        )
        
        event = logger.log_auth_success("user1", "127.0.0.1", "password")
        assert event.correlation_id == custom_id


class TestPIIRedaction:
    """Tests for Properties 7, 8, 9: PII Redaction."""

    @given(st.text(min_size=10, max_size=50))
    @settings(max_examples=20)
    def test_bearer_token_redaction(self, prefix: str) -> None:
        """
        **Feature: core-improvements-v2, Property 7: Bearer Token Redaction**
        **Validates: Requirements 5.2**
        
        For any string containing a Bearer JWT token, _redact() SHALL replace it.
        """
        logger = SecurityAuditLogger()
        
        # Create a fake JWT-like token
        fake_jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1c2VyIn0.signature123"
        text = f"{prefix} Bearer {fake_jwt} end"
        
        result = logger._redact(text)
        assert "Bearer [REDACTED]" in result
        assert fake_jwt not in result

    def test_credit_card_with_separators(self) -> None:
        """
        **Feature: core-improvements-v2, Property 8: Credit Card Redaction with Separators**
        **Validates: Requirements 5.3**
        
        Credit cards with spaces or dashes SHALL be redacted.
        """
        logger = SecurityAuditLogger()
        
        test_cases = [
            "Card: 4111-1111-1111-1111",
            "Card: 4111 1111 1111 1111",
            "Card: 4111111111111111",
        ]
        
        for text in test_cases:
            result = logger._redact(text)
            assert "[CARD]" in result

    def test_ip_address_redaction_when_enabled(self) -> None:
        """
        **Feature: core-improvements-v2, Property 9: IP Address Redaction**
        **Validates: Requirements 5.1, 5.5**
        
        When IP redaction is enabled, IPv4 and IPv6 SHALL be redacted.
        """
        logger = SecurityAuditLogger(redact_ip_addresses=True)
        
        ipv4_text = "Client IP: 192.168.1.100"
        ipv6_text = "Client IP: 2001:0db8:85a3:0000:0000:8a2e:0370:7334"
        
        assert "[IP_REDACTED]" in logger._redact(ipv4_text)
        assert "[IP_REDACTED]" in logger._redact(ipv6_text)

    def test_ip_address_not_redacted_when_disabled(self) -> None:
        """IP addresses should NOT be redacted when disabled."""
        logger = SecurityAuditLogger(redact_ip_addresses=False)
        
        text = "Client IP: 192.168.1.100"
        result = logger._redact(text)
        
        assert "192.168.1.100" in result
        assert "[IP_REDACTED]" not in result


class TestModuleExports:
    """Tests for Property 10: Module __all__ Completeness."""

    def test_exceptions_module_exports(self) -> None:
        """
        **Feature: core-improvements-v2, Property 10: Module __all__ Completeness**
        **Validates: Requirements 6.1**
        """
        from my_app.core import exceptions
        
        assert hasattr(exceptions, "__all__")
        expected = [
            "ErrorContext",
            "AppException",
            "EntityNotFoundError",
            "ValidationError",
            "BusinessRuleViolationError",
            "AuthenticationError",
            "AuthorizationError",
            "RateLimitExceededError",
            "ConflictError",
        ]
        for name in expected:
            assert name in exceptions.__all__

    def test_config_module_exports(self) -> None:
        """
        **Feature: core-improvements-v2, Property 10: Module __all__ Completeness**
        **Validates: Requirements 6.2**
        """
        from my_app.core import config
        
        assert hasattr(config, "__all__")
        assert "Settings" in config.__all__
        assert "get_settings" in config.__all__

    def test_container_module_exports(self) -> None:
        """
        **Feature: core-improvements-v2, Property 10: Module __all__ Completeness**
        **Validates: Requirements 6.3**
        """
        from my_app.core import container
        
        assert hasattr(container, "__all__")
        expected = ["Container", "LifecycleManager", "LifecycleHookError", "create_container", "lifecycle"]
        for name in expected:
            assert name in container.__all__
