"""Unit tests for JWT providers (ES256 and RS256).

**Feature: test-coverage-90-percent**
"""

import pytest
from datetime import timedelta
from unittest.mock import patch, MagicMock

from infrastructure.auth.jwt.es256_provider import ES256Provider
from infrastructure.auth.jwt.rs256_provider import RS256Provider
from infrastructure.auth.jwt.exceptions import InvalidKeyError


# Test PEM keys (for testing only - not real keys)
MOCK_RSA_PRIVATE_KEY = """-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEA0Z3VS5JJcds3xfn/ygWyF8PbnGy0AHB7MmM8aabbcc
-----END RSA PRIVATE KEY-----"""

MOCK_RSA_PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA0Z3VS5JJcds3xfn
-----END PUBLIC KEY-----"""

MOCK_EC_PRIVATE_KEY = """-----BEGIN EC PRIVATE KEY-----
MHQCAQEEIBYr17dBrzGqVj0gVgrFb/cWbj0hZmTNqDg8GMHy
-----END EC PRIVATE KEY-----"""

MOCK_EC_PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAEjXfA
-----END PUBLIC KEY-----"""


class TestRS256Provider:
    """Tests for RS256Provider."""

    def test_init_with_private_key(self) -> None:
        """Should initialize with private key only."""
        with patch.object(RS256Provider, '_generate_kid', return_value='test-kid'):
            provider = RS256Provider(private_key=MOCK_RSA_PRIVATE_KEY)
            assert provider.algorithm == "RS256"

    def test_init_with_public_key(self) -> None:
        """Should initialize with public key only."""
        with patch.object(RS256Provider, '_generate_kid', return_value='test-kid'):
            provider = RS256Provider(public_key=MOCK_RSA_PUBLIC_KEY)
            assert provider.algorithm == "RS256"

    def test_init_with_both_keys(self) -> None:
        """Should initialize with both keys."""
        with patch.object(RS256Provider, '_generate_kid', return_value='test-kid'):
            provider = RS256Provider(
                private_key=MOCK_RSA_PRIVATE_KEY,
                public_key=MOCK_RSA_PUBLIC_KEY,
            )
            assert provider.algorithm == "RS256"

    def test_init_without_keys_raises_error(self) -> None:
        """Should raise error when no keys provided."""
        with pytest.raises(InvalidKeyError) as exc_info:
            RS256Provider()
        assert "RS256 requires at least one" in str(exc_info.value)

    def test_init_with_invalid_private_key_format(self) -> None:
        """Should raise error for invalid private key format."""
        with pytest.raises(InvalidKeyError) as exc_info:
            RS256Provider(private_key="invalid-key")
        assert "Invalid RSA private key format" in str(exc_info.value)

    def test_init_with_invalid_public_key_format(self) -> None:
        """Should raise error for invalid public key format."""
        with pytest.raises(InvalidKeyError) as exc_info:
            RS256Provider(public_key="invalid-key")
        assert "Invalid RSA public key format" in str(exc_info.value)

    def test_init_with_custom_params(self) -> None:
        """Should accept custom issuer, audience, and expiry."""
        with patch.object(RS256Provider, '_generate_kid', return_value='test-kid'):
            provider = RS256Provider(
                private_key=MOCK_RSA_PRIVATE_KEY,
                issuer="test-issuer",
                audience="test-audience",
                default_expiry=timedelta(hours=2),
            )
            assert provider._issuer == "test-issuer"
            assert provider._audience == "test-audience"

    def test_init_with_custom_kid(self) -> None:
        """Should use custom kid when provided."""
        provider = RS256Provider(
            private_key=MOCK_RSA_PRIVATE_KEY,
            kid="custom-kid",
        )
        assert provider._kid == "custom-kid"

    def test_get_signing_key_without_private_key(self) -> None:
        """Should raise error when signing without private key."""
        with patch.object(RS256Provider, '_generate_kid', return_value='test-kid'):
            provider = RS256Provider(public_key=MOCK_RSA_PUBLIC_KEY)
            with pytest.raises(InvalidKeyError) as exc_info:
                provider._get_signing_key()
            assert "Private key required" in str(exc_info.value)

    def test_get_verification_key_with_public_key(self) -> None:
        """Should return public key for verification."""
        with patch.object(RS256Provider, '_generate_kid', return_value='test-kid'):
            provider = RS256Provider(public_key=MOCK_RSA_PUBLIC_KEY)
            key = provider._get_verification_key()
            assert key == MOCK_RSA_PUBLIC_KEY

    def test_get_verification_key_fallback_to_private(self) -> None:
        """Should fallback to private key for verification."""
        with patch.object(RS256Provider, '_generate_kid', return_value='test-kid'):
            provider = RS256Provider(private_key=MOCK_RSA_PRIVATE_KEY)
            key = provider._get_verification_key()
            assert key == MOCK_RSA_PRIVATE_KEY


class TestES256Provider:
    """Tests for ES256Provider."""

    def test_init_with_private_key(self) -> None:
        """Should initialize with private key only."""
        with patch.object(ES256Provider, '_generate_kid', return_value='test-kid'):
            provider = ES256Provider(private_key=MOCK_EC_PRIVATE_KEY)
            assert provider.algorithm == "ES256"

    def test_init_with_public_key(self) -> None:
        """Should initialize with public key only."""
        with patch.object(ES256Provider, '_generate_kid', return_value='test-kid'):
            provider = ES256Provider(public_key=MOCK_EC_PUBLIC_KEY)
            assert provider.algorithm == "ES256"

    def test_init_with_both_keys(self) -> None:
        """Should initialize with both keys."""
        with patch.object(ES256Provider, '_generate_kid', return_value='test-kid'):
            provider = ES256Provider(
                private_key=MOCK_EC_PRIVATE_KEY,
                public_key=MOCK_EC_PUBLIC_KEY,
            )
            assert provider.algorithm == "ES256"

    def test_init_without_keys_raises_error(self) -> None:
        """Should raise error when no keys provided."""
        with pytest.raises(InvalidKeyError) as exc_info:
            ES256Provider()
        assert "ES256 requires at least one" in str(exc_info.value)

    def test_init_with_invalid_private_key_format(self) -> None:
        """Should raise error for invalid private key format."""
        with pytest.raises(InvalidKeyError) as exc_info:
            ES256Provider(private_key="invalid-key")
        assert "Invalid ECDSA private key format" in str(exc_info.value)

    def test_init_with_invalid_public_key_format(self) -> None:
        """Should raise error for invalid public key format."""
        with pytest.raises(InvalidKeyError) as exc_info:
            ES256Provider(public_key="invalid-key")
        assert "Invalid ECDSA public key format" in str(exc_info.value)

    def test_init_with_custom_params(self) -> None:
        """Should accept custom issuer, audience, and expiry."""
        with patch.object(ES256Provider, '_generate_kid', return_value='test-kid'):
            provider = ES256Provider(
                private_key=MOCK_EC_PRIVATE_KEY,
                issuer="test-issuer",
                audience="test-audience",
                default_expiry=timedelta(hours=2),
            )
            assert provider._issuer == "test-issuer"
            assert provider._audience == "test-audience"

    def test_init_with_custom_kid(self) -> None:
        """Should use custom kid when provided."""
        provider = ES256Provider(
            private_key=MOCK_EC_PRIVATE_KEY,
            kid="custom-kid",
        )
        assert provider._kid == "custom-kid"

    def test_get_signing_key_without_private_key(self) -> None:
        """Should raise error when signing without private key."""
        with patch.object(ES256Provider, '_generate_kid', return_value='test-kid'):
            provider = ES256Provider(public_key=MOCK_EC_PUBLIC_KEY)
            with pytest.raises(InvalidKeyError) as exc_info:
                provider._get_signing_key()
            assert "Private key required" in str(exc_info.value)

    def test_get_verification_key_with_public_key(self) -> None:
        """Should return public key for verification."""
        with patch.object(ES256Provider, '_generate_kid', return_value='test-kid'):
            provider = ES256Provider(public_key=MOCK_EC_PUBLIC_KEY)
            key = provider._get_verification_key()
            assert key == MOCK_EC_PUBLIC_KEY

    def test_get_verification_key_fallback_to_private(self) -> None:
        """Should fallback to private key for verification."""
        with patch.object(ES256Provider, '_generate_kid', return_value='test-kid'):
            provider = ES256Provider(private_key=MOCK_EC_PRIVATE_KEY)
            key = provider._get_verification_key()
            assert key == MOCK_EC_PRIVATE_KEY
