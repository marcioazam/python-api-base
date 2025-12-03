"""Property-based tests for JWT Encode/Decode Round-Trip.

**Feature: architecture-restructuring-2025, Property 12: JWT Encode/Decode Round-Trip**
**Validates: Requirements 9.2**
"""

import pytest
from datetime import timedelta
from hypothesis import given, settings
from hypothesis import strategies as st

try:
    from infrastructure.security.token_service import (
        HS256Provider,
        InvalidKeyError,
    )
except ImportError:
    pytest.skip("my_app modules not available", allow_module_level=True)


# Strategy for claim values
claim_key_strategy = st.text(
    min_size=1, max_size=20,
    alphabet="abcdefghijklmnopqrstuvwxyz_"
)
claim_value_strategy = st.one_of(
    st.text(max_size=100),
    st.integers(min_value=-1000000, max_value=1000000),
    st.booleans(),
    st.lists(st.text(max_size=20), max_size=5),
)

# Strategy for claims dictionary
claims_strategy = st.dictionaries(
    keys=claim_key_strategy,
    values=claim_value_strategy,
    min_size=1,
    max_size=5,
).filter(lambda d: "exp" not in d and "iat" not in d and "iss" not in d and "aud" not in d)

# Strategy for subject claim
subject_strategy = st.text(min_size=1, max_size=50, alphabet="abcdefghijklmnopqrstuvwxyz0123456789-_")


class TestJWTRoundTrip:
    """Property tests for JWT encode/decode round-trip."""

    @settings(max_examples=50)
    @given(subject=subject_strategy)
    def test_sign_verify_roundtrip_preserves_subject(self, subject: str) -> None:
        """
        **Feature: architecture-restructuring-2025, Property 12: JWT Encode/Decode Round-Trip**
        
        For any subject claim, encoding to JWT and decoding back
        SHALL preserve the subject.
        **Validates: Requirements 9.2**
        """
        provider = HS256Provider(
            secret_key="test-secret-key-at-least-32-characters-long",
            default_expiry=timedelta(hours=1),
        )
        
        token = provider.sign({"sub": subject})
        claims = provider.verify(token)
        
        assert claims["sub"] == subject

    @settings(max_examples=50)
    @given(claims=claims_strategy)
    def test_sign_verify_roundtrip_preserves_claims(self, claims: dict) -> None:
        """
        For any valid claims dictionary, encoding to JWT and decoding back
        SHALL preserve all original claims.
        **Validates: Requirements 9.2**
        """
        provider = HS256Provider(
            secret_key="test-secret-key-at-least-32-characters-long",
            default_expiry=timedelta(hours=1),
        )
        
        token = provider.sign(claims)
        decoded = provider.verify(token)
        
        # All original claims should be present
        for key, value in claims.items():
            assert key in decoded
            assert decoded[key] == value

    @settings(max_examples=30)
    @given(subject=subject_strategy)
    def test_issuer_and_audience_preserved(self, subject: str) -> None:
        """
        For any token with issuer and audience, these claims SHALL be preserved.
        **Validates: Requirements 9.2**
        """
        provider = HS256Provider(
            secret_key="test-secret-key-at-least-32-characters-long",
            issuer="test-issuer",
            audience="test-audience",
            default_expiry=timedelta(hours=1),
        )
        
        token = provider.sign({"sub": subject})
        claims = provider.verify(token)
        
        assert claims["iss"] == "test-issuer"
        assert claims["aud"] == "test-audience"
        assert claims["sub"] == subject

    @settings(max_examples=30)
    @given(subject=subject_strategy)
    def test_token_contains_standard_claims(self, subject: str) -> None:
        """
        For any signed token, standard JWT claims (iat, exp) SHALL be present.
        **Validates: Requirements 9.2**
        """
        provider = HS256Provider(
            secret_key="test-secret-key-at-least-32-characters-long",
            default_expiry=timedelta(hours=1),
        )
        
        token = provider.sign({"sub": subject})
        claims = provider.verify(token)
        
        assert "iat" in claims  # Issued at
        assert "exp" in claims  # Expiration

    @settings(max_examples=20)
    @given(
        roles=st.lists(st.text(min_size=1, max_size=20), min_size=1, max_size=5, unique=True)
    )
    def test_list_claims_preserved(self, roles: list[str]) -> None:
        """
        For any list claim (like roles), encoding and decoding SHALL preserve the list.
        **Validates: Requirements 9.2**
        """
        provider = HS256Provider(
            secret_key="test-secret-key-at-least-32-characters-long",
            default_expiry=timedelta(hours=1),
        )
        
        token = provider.sign({"roles": roles})
        claims = provider.verify(token)
        
        assert claims["roles"] == roles

    def test_wrong_secret_fails_verification(self) -> None:
        """
        For any token, verifying with wrong secret SHALL fail.
        **Validates: Requirements 9.2**
        """
        provider1 = HS256Provider(
            secret_key="first-secret-key-at-least-32-characters",
            default_expiry=timedelta(hours=1),
        )
        provider2 = HS256Provider(
            secret_key="second-secret-key-at-least-32-chars",
            default_expiry=timedelta(hours=1),
        )
        
        token = provider1.sign({"sub": "user123"})
        
        with pytest.raises(InvalidKeyError):
            provider2.verify(token)
