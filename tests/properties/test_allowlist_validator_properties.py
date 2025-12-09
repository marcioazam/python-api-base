'''Property-based tests for Allowlist Validator.'''

from uuid import uuid4
import pytest
from hypothesis import given, settings, strategies as st, HealthCheck
from core.shared.validation.allowlist_validator import (
    AllowlistValidator,
    validate_email,
    validate_uuid,
    validate_url,
)


class TestAllowlistValidatorEnforcement:
    '''Property tests for allowlist validator enforcement.'''

    @given(st.sets(st.text(min_size=1, max_size=10), min_size=1, max_size=5))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_values_in_allowlist_pass_validation(self, allowed):
        validator = AllowlistValidator(allowed)
        for value in allowed:
            result = validator.validate(value)
            assert result.is_ok()

    def test_empty_allowlist_rejects_all_values(self):
        validator = AllowlistValidator(set())
        result = validator.validate('test')
        assert result.is_err()


class TestDomainValidators:
    '''Property tests for domain validators.'''

    def test_valid_uuid_format(self):
        valid_uuid = str(uuid4())
        result = validate_uuid(valid_uuid)
        assert result.is_ok()

    def test_invalid_uuid_formats(self):
        result = validate_uuid('not-a-uuid')
        assert result.is_err()

    def test_valid_url_formats(self):
        result = validate_url('https://example.com')
        assert result.is_ok()

    def test_invalid_url_schemes(self):
        result = validate_url('http://example.com')
        assert result.is_err()
