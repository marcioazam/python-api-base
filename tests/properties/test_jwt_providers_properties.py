"""Property-based tests for JWT providers.

**Feature: api-base-score-100, Task 1.3: Write property test for RS256 round-trip**
**Feature: api-base-score-100, Task 1.4: Write property test for algorithm mismatch**
**Validates: Requirements 1.2, 1.3**
"""

from datetime import timedelta

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from hypothesis import given, settings, strategies as st

from my_app.core.auth.jwt_providers import (
    AlgorithmMismatchError,
    ES256Provider,
    HS256Provider,
    InvalidKeyError,
    RS256Provider,
)


def generate_rsa_key_pair() -> tuple[str, str]:
    """Generate RSA key pair for testing."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")

    return private_pem, public_pem


def generate_ec_key_pair() -> tuple[str, str]:
    """Generate ECDSA key pair for testing."""
    private_key = ec.generate_private_key(ec.SECP256R1())
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")

    return private_pem, public_pem


# Generate keys once for all tests
RSA_PRIVATE_KEY, RSA_PUBLIC_KEY = generate_rsa_key_pair()
EC_PRIVATE_KEY, EC_PUBLIC_KEY = generate_ec_key_pair()


# Strategy for valid JWT payload claims
jwt_payload_strategy = st.fixed_dictionaries({
    "sub": st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("L", "N"))),
    "jti": st.uuids().map(str),
}).filter(lambda x: len(x["sub"]) > 0)


class TestRS256RoundTrip:
    """Property tests for RS256 sign-verify round trip.

    **Feature: api-base-score-100, Property 1: RS256 Sign-Verify Round Trip**
    **Validates: Requirements 1.2**
    """

    @given(payload=jwt_payload_strategy)
    @settings(max_examples=100)
    def test_rs256_sign_verify_round_trip(self, payload: dict) -> None:
        """For any valid payload, sign then verify returns original claims.

        **Feature: api-base-score-100, Property 1: RS256 Sign-Verify Round Trip**
        **Validates: Requirements 1.2**
        """
        provider = RS256Provider(
            private_key=RSA_PRIVATE_KEY,
            public_key=RSA_PUBLIC_KEY,
        )

        token = provider.sign(payload)
        claims = provider.verify(token)

        assert claims["sub"] == payload["sub"]
        assert claims["jti"] == payload["jti"]

    @given(payload=jwt_payload_strategy)
    @settings(max_examples=100)
    def test_es256_sign_verify_round_trip(self, payload: dict) -> None:
        """For any valid payload, ES256 sign then verify returns original claims.

        **Feature: api-base-score-100, Property 1: RS256 Sign-Verify Round Trip**
        **Validates: Requirements 1.2**
        """
        provider = ES256Provider(
            private_key=EC_PRIVATE_KEY,
            public_key=EC_PUBLIC_KEY,
        )

        token = provider.sign(payload)
        claims = provider.verify(token)

        assert claims["sub"] == payload["sub"]
        assert claims["jti"] == payload["jti"]

    @given(payload=jwt_payload_strategy)
    @settings(max_examples=100)
    def test_hs256_sign_verify_round_trip(self, payload: dict) -> None:
        """For any valid payload, HS256 sign then verify returns original claims.

        **Feature: api-base-score-100, Property 1: RS256 Sign-Verify Round Trip**
        **Validates: Requirements 1.2**
        """
        provider = HS256Provider(
            secret_key="a" * 32,  # Minimum 32 chars
        )

        token = provider.sign(payload)
        claims = provider.verify(token)

        assert claims["sub"] == payload["sub"]
        assert claims["jti"] == payload["jti"]


class TestAlgorithmMismatch:
    """Property tests for algorithm mismatch rejection.

    **Feature: api-base-score-100, Property 2: Algorithm Mismatch Rejection**
    **Validates: Requirements 1.3**
    """

    @given(payload=jwt_payload_strategy)
    @settings(max_examples=100)
    def test_rs256_token_rejected_by_es256(self, payload: dict) -> None:
        """Token signed with RS256 rejected by ES256 verifier.

        **Feature: api-base-score-100, Property 2: Algorithm Mismatch Rejection**
        **Validates: Requirements 1.3**
        """
        rs256_provider = RS256Provider(
            private_key=RSA_PRIVATE_KEY,
            public_key=RSA_PUBLIC_KEY,
        )
        es256_provider = ES256Provider(
            private_key=EC_PRIVATE_KEY,
            public_key=EC_PUBLIC_KEY,
        )

        token = rs256_provider.sign(payload)

        with pytest.raises(AlgorithmMismatchError) as exc_info:
            es256_provider.verify(token)

        assert exc_info.value.expected == "ES256"
        assert exc_info.value.received == "RS256"

    @given(payload=jwt_payload_strategy)
    @settings(max_examples=100)
    def test_es256_token_rejected_by_rs256(self, payload: dict) -> None:
        """Token signed with ES256 rejected by RS256 verifier.

        **Feature: api-base-score-100, Property 2: Algorithm Mismatch Rejection**
        **Validates: Requirements 1.3**
        """
        es256_provider = ES256Provider(
            private_key=EC_PRIVATE_KEY,
            public_key=EC_PUBLIC_KEY,
        )
        rs256_provider = RS256Provider(
            private_key=RSA_PRIVATE_KEY,
            public_key=RSA_PUBLIC_KEY,
        )

        token = es256_provider.sign(payload)

        with pytest.raises(AlgorithmMismatchError) as exc_info:
            rs256_provider.verify(token)

        assert exc_info.value.expected == "RS256"
        assert exc_info.value.received == "ES256"

    @given(payload=jwt_payload_strategy)
    @settings(max_examples=100)
    def test_hs256_token_rejected_by_rs256(self, payload: dict) -> None:
        """Token signed with HS256 rejected by RS256 verifier.

        **Feature: api-base-score-100, Property 2: Algorithm Mismatch Rejection**
        **Validates: Requirements 1.3**
        """
        hs256_provider = HS256Provider(secret_key="a" * 32)
        rs256_provider = RS256Provider(
            private_key=RSA_PRIVATE_KEY,
            public_key=RSA_PUBLIC_KEY,
        )

        token = hs256_provider.sign(payload)

        with pytest.raises(AlgorithmMismatchError) as exc_info:
            rs256_provider.verify(token)

        assert exc_info.value.expected == "RS256"
        assert exc_info.value.received == "HS256"


class TestInvalidKeyFormat:
    """Tests for invalid key format errors.

    **Feature: api-base-score-100, Property 3: Invalid Key Format Error**
    **Validates: Requirements 1.5**
    """

    def test_rs256_invalid_private_key_format(self) -> None:
        """RS256 with invalid private key raises InvalidKeyError."""
        with pytest.raises(InvalidKeyError) as exc_info:
            RS256Provider(private_key="not-a-valid-key")

        assert "PEM format" in str(exc_info.value)

    def test_es256_invalid_private_key_format(self) -> None:
        """ES256 with invalid private key raises InvalidKeyError."""
        with pytest.raises(InvalidKeyError) as exc_info:
            ES256Provider(private_key="not-a-valid-key")

        assert "PEM format" in str(exc_info.value)

    def test_hs256_short_secret_key(self) -> None:
        """HS256 with short secret key raises InvalidKeyError."""
        with pytest.raises(InvalidKeyError) as exc_info:
            HS256Provider(secret_key="short")

        assert "32 characters" in str(exc_info.value)

    def test_rs256_no_keys_provided(self) -> None:
        """RS256 with no keys raises InvalidKeyError."""
        with pytest.raises(InvalidKeyError) as exc_info:
            RS256Provider()

        assert "private_key or public_key" in str(exc_info.value)

    def test_es256_no_keys_provided(self) -> None:
        """ES256 with no keys raises InvalidKeyError."""
        with pytest.raises(InvalidKeyError) as exc_info:
            ES256Provider()

        assert "private_key or public_key" in str(exc_info.value)
