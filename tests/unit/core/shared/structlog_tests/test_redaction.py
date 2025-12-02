"""Unit tests for PII redaction processor.

**Feature: observability-infrastructure**
**Requirement: R1.5 - PII Redaction**
"""

import pytest

from core.shared.logging.redaction import (
    RedactionProcessor,
    PIIPattern,
    PII_PATTERNS,
    create_redaction_processor,
)


class TestRedactionProcessor:
    """Tests for RedactionProcessor."""

    def test_redact_email(self) -> None:
        """Test email address redaction."""
        processor = RedactionProcessor()
        event = {"event": "User admin@example.com logged in"}

        result = processor(None, "info", event)

        assert "ad***@example.com" in result["event"]
        assert "admin@example.com" not in result["event"]

    def test_redact_multiple_emails(self) -> None:
        """Test redaction of multiple emails."""
        processor = RedactionProcessor()
        event = {"event": "Users test1@domain.com and test2@domain.org registered"}

        result = processor(None, "info", event)

        assert "te***@domain.com" in result["event"]
        assert "te***@domain.org" in result["event"]
        assert "test1@domain.com" not in result["event"]

    def test_redact_password_json(self) -> None:
        """Test password redaction in JSON format."""
        processor = RedactionProcessor()
        event = {"event": '{"password": "secret123", "user": "admin"}'}

        result = processor(None, "info", event)

        assert '"password": "***"' in result["event"]
        assert "secret123" not in result["event"]

    def test_redact_password_field(self) -> None:
        """Test password redaction in field format."""
        processor = RedactionProcessor()
        event = {"event": "Login attempt: password=mysecret user=admin"}

        result = processor(None, "info", event)

        assert "password=***" in result["event"]
        assert "mysecret" not in result["event"]

    def test_redact_credit_card(self) -> None:
        """Test credit card number redaction."""
        processor = RedactionProcessor()
        event = {"event": "Payment with card 4111-1111-1111-1234"}

        result = processor(None, "info", event)

        assert "****-****-****-1234" in result["event"]
        assert "4111-1111-1111-1234" not in result["event"]

    def test_redact_credit_card_no_dashes(self) -> None:
        """Test credit card without dashes."""
        processor = RedactionProcessor()
        event = {"event": "Card number: 4111111111111234"}

        result = processor(None, "info", event)

        assert "****-****-****-1234" in result["event"]

    def test_redact_ssn(self) -> None:
        """Test SSN redaction."""
        processor = RedactionProcessor()
        event = {"event": "SSN: 123-45-6789"}

        result = processor(None, "info", event)

        assert "***-**-****" in result["event"]
        assert "123-45-6789" not in result["event"]

    def test_redact_cpf(self) -> None:
        """Test Brazilian CPF redaction."""
        processor = RedactionProcessor()
        event = {"event": "CPF: 123.456.789-00"}

        result = processor(None, "info", event)

        assert "***-**-****" in result["event"]
        assert "123.456.789-00" not in result["event"]

    def test_redact_phone(self) -> None:
        """Test phone number redaction."""
        processor = RedactionProcessor()
        event = {"event": "Phone: (555) 123-4567"}

        result = processor(None, "info", event)

        assert "***-***-4567" in result["event"]
        assert "(555) 123-4567" not in result["event"]

    def test_redact_bearer_token(self) -> None:
        """Test Bearer token redaction."""
        processor = RedactionProcessor()
        event = {"event": "Auth: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.payload.signature"}

        result = processor(None, "info", event)

        assert "Bearer ***" in result["event"]
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in result["event"]

    def test_redact_api_key(self) -> None:
        """Test API key redaction."""
        processor = RedactionProcessor()
        event = {"event": 'Headers: {"api_key": "sk-1234567890abcdef1234567890abcdef"}'}

        result = processor(None, "info", event)

        assert "***" in result["event"]
        assert "sk-1234567890abcdef1234567890abcdef" not in result["event"]

    def test_redact_sensitive_field_names(self) -> None:
        """Test complete redaction of sensitive field names."""
        processor = RedactionProcessor()
        event = {
            "event": "Login",
            "password": "secret",
            "token": "abc123",
            "api_key": "key123",
            "user": "admin",  # Should not be redacted
        }

        result = processor(None, "info", event)

        assert result["password"] == "***"
        assert result["token"] == "***"
        assert result["api_key"] == "***"
        assert result["user"] == "admin"

    def test_preserve_safe_fields(self) -> None:
        """Test that safe fields are not redacted."""
        processor = RedactionProcessor()
        event = {
            "@timestamp": "2024-12-01T12:00:00Z",
            "log.level": "INFO",
            "correlation_id": "abc-123",
            "service.name": "test-service",
        }

        result = processor(None, "info", event)

        assert result["@timestamp"] == "2024-12-01T12:00:00Z"
        assert result["log.level"] == "INFO"
        assert result["correlation_id"] == "abc-123"
        assert result["service.name"] == "test-service"

    def test_redact_nested_dict(self) -> None:
        """Test redaction in nested dictionaries."""
        processor = RedactionProcessor()
        event = {
            "event": "Request",
            "data": {
                "email": "test@example.com",
                "password": "secret",
            },
        }

        result = processor(None, "info", event)

        assert result["data"]["password"] == "***"
        # Email in nested dict is a string value, not redacted by field name
        # but would be redacted if it appeared in a string

    def test_redact_list(self) -> None:
        """Test redaction in lists."""
        processor = RedactionProcessor()
        event = {
            "event": "Batch",
            "items": [
                {"name": "item1", "password": "secret1"},
                {"name": "item2", "password": "secret2"},
            ],
        }

        result = processor(None, "info", event)

        assert result["items"][0]["password"] == "***"
        assert result["items"][1]["password"] == "***"

    def test_disabled_processor(self) -> None:
        """Test that disabled processor passes through unchanged."""
        processor = RedactionProcessor(enabled=False)
        event = {"event": "Email: admin@example.com", "password": "secret"}

        result = processor(None, "info", event)

        assert result["event"] == "Email: admin@example.com"
        assert result["password"] == "secret"

    def test_add_custom_pattern(self) -> None:
        """Test adding custom PII pattern."""
        import re

        processor = RedactionProcessor()
        processor.add_pattern(
            "custom_id",
            PIIPattern(
                name="custom_id",
                pattern=re.compile(r"CUST-\d{6}"),
                replacement="CUST-******",
            ),
        )

        event = {"event": "Customer CUST-123456 registered"}
        result = processor(None, "info", event)

        assert "CUST-******" in result["event"]
        assert "CUST-123456" not in result["event"]

    def test_remove_pattern(self) -> None:
        """Test removing PII pattern."""
        processor = RedactionProcessor()
        processor.remove_pattern("email")

        event = {"event": "User admin@example.com logged in"}
        result = processor(None, "info", event)

        # Email should not be redacted after pattern removal
        assert "admin@example.com" in result["event"]


class TestCreateRedactionProcessor:
    """Tests for create_redaction_processor factory."""

    def test_create_with_defaults(self) -> None:
        """Test creating processor with default settings."""
        processor = create_redaction_processor()

        assert processor.enabled is True
        assert len(processor.patterns) == len(PII_PATTERNS)

    def test_create_disabled(self) -> None:
        """Test creating disabled processor."""
        processor = create_redaction_processor(enabled=False)

        assert processor.enabled is False

    def test_create_with_extra_patterns(self) -> None:
        """Test creating processor with extra patterns."""
        import re

        extra = {
            "custom": PIIPattern(
                name="custom",
                pattern=re.compile(r"SECRET-\w+"),
                replacement="SECRET-***",
            )
        }

        processor = create_redaction_processor(extra_patterns=extra)

        assert "custom" in processor.patterns

    def test_create_with_extra_fields(self) -> None:
        """Test creating processor with extra sensitive fields."""
        processor = create_redaction_processor(extra_fields={"custom_secret"})

        assert "custom_secret" in processor.fields_to_redact
