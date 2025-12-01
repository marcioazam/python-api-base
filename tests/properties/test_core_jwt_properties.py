"""Property-based tests for core JWT module.

**Feature: core-code-review**
**Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5, 5.1, 5.2, 5.4, 5.5**
"""

import string
from datetime import datetime, timedelta, timezone

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from my_app.core.auth.jwt import (
    JWTService,
    TokenPayload,
    TokenPair,
    TokenExpiredError,
    TokenInvalidError,
    TokenRevokedError,
    TimeSource,
)


class MockTimeSource:
    """Mock time source for testing."""
    
    def __init__(self, fixed_time: datetime | None = None):
        self._time = fixed_time or datetime.now(timezone.utc)
    
    def now(self) -> datetime:
        return self._time
    
    def advance(self, delta: timedelta) -> None:
        self._time = self._time + delta


class TestJWTRequiredClaims:
    """Property tests for JWT required claims.
    
    **Feature: core-code-review, Property 6: JWT Required Claims**
    **Validates: Requirements 4.1**
    """

    @given(
        user_id=st.text(min_size=1, max_size=50, alphabet=string.ascii_letters + string.digits),
        scopes=st.lists(st.text(min_size=1, max_size=20, alphabet=string.ascii_lowercase), max_size=5),
    )
    @settings(max_examples=100)
    def test_access_token_contains_required_claims(self, user_id: str, scopes: list[str]):
        """For any user_id, created token SHALL contain sub, exp, iat, jti."""
        assume(len(user_id) > 0)
        
        service = JWTService(secret_key="a" * 32)
        token, payload = service.create_access_token(user_id, scopes)
        
        # Required claims must be present
        assert payload.sub == user_id
        assert payload.exp is not None
        assert payload.iat is not None
        assert payload.jti is not None
        assert len(payload.jti) > 0
        
        # Token type should be access
        assert payload.token_type == "access"
        
        # Scopes should match
        assert list(payload.scopes) == scopes

    @given(user_id=st.text(min_size=1, max_size=50, alphabet=string.ascii_letters))
    @settings(max_examples=100)
    def test_refresh_token_contains_required_claims(self, user_id: str):
        """For any user_id, refresh token SHALL contain required claims."""
        assume(len(user_id) > 0)
        
        service = JWTService(secret_key="a" * 32)
        token, payload = service.create_refresh_token(user_id)
        
        assert payload.sub == user_id
        assert payload.exp is not None
        assert payload.iat is not None
        assert payload.jti is not None
        assert payload.token_type == "refresh"


class TestJWTClockSkew:
    """Property tests for JWT clock skew tolerance.
    
    **Feature: core-code-review**
    **Validates: Requirements 4.4**
    """

    @given(skew_seconds=st.integers(min_value=1, max_value=120))
    @settings(max_examples=50)
    def test_token_valid_within_clock_skew(self, skew_seconds: int):
        """Token SHALL be valid within clock skew tolerance."""
        time_source = MockTimeSource()
        service = JWTService(
            secret_key="a" * 32,
            access_token_expire_minutes=1,
            clock_skew_seconds=skew_seconds,
            time_source=time_source,
        )
        
        token, _ = service.create_access_token("user123")
        
        # Advance time to just after expiration but within skew
        time_source.advance(timedelta(minutes=1, seconds=skew_seconds - 1))
        
        # Should still be valid
        payload = service.verify_token(token)
        assert payload.sub == "user123"


class TestRefreshTokenReplayProtection:
    """Property tests for refresh token replay protection.
    
    **Feature: core-code-review**
    **Validates: Requirements 4.5**
    """

    @given(user_id=st.text(min_size=1, max_size=50, alphabet=string.ascii_letters))
    @settings(max_examples=50)
    def test_refresh_token_cannot_be_reused(self, user_id: str):
        """For any refresh token, second use SHALL raise TokenRevokedError."""
        assume(len(user_id) > 0)
        
        service = JWTService(secret_key="a" * 32)
        token, _ = service.create_refresh_token(user_id)
        
        # First use should succeed
        payload = service.verify_refresh_token(token)
        assert payload.sub == user_id
        
        # Second use should fail
        with pytest.raises(TokenRevokedError):
            service.verify_refresh_token(token)

    @given(
        user_ids=st.lists(
            st.text(min_size=1, max_size=20, alphabet=string.ascii_letters),
            min_size=2,
            max_size=5,
            unique=True,
        )
    )
    @settings(max_examples=50)
    def test_different_refresh_tokens_independent(self, user_ids: list[str]):
        """Different refresh tokens SHALL be independent."""
        assume(all(len(uid) > 0 for uid in user_ids))
        
        service = JWTService(secret_key="a" * 32)
        tokens = [service.create_refresh_token(uid)[0] for uid in user_ids]
        
        # Each token should be usable once
        for i, token in enumerate(tokens):
            payload = service.verify_refresh_token(token)
            assert payload.sub == user_ids[i]


class TestTokenPayloadSerialization:
    """Property tests for token payload serialization.
    
    **Feature: core-code-review, Property 24: Token Serialization Round-Trip**
    **Validates: Requirements 12.2**
    """

    @given(
        user_id=st.text(min_size=1, max_size=50, alphabet=string.ascii_letters),
        scopes=st.lists(st.text(min_size=1, max_size=20, alphabet=string.ascii_lowercase), max_size=5),
    )
    @settings(max_examples=100)
    def test_token_payload_round_trip(self, user_id: str, scopes: list[str]):
        """For any TokenPayload, to_dict/from_dict SHALL round-trip correctly."""
        assume(len(user_id) > 0)
        
        now = datetime.now(timezone.utc)
        payload = TokenPayload(
            sub=user_id,
            exp=now + timedelta(hours=1),
            iat=now,
            jti="test-jti-123",
            scopes=tuple(scopes),
            token_type="access",
        )
        
        # Round-trip
        data = payload.to_dict()
        restored = TokenPayload.from_dict(data)
        
        assert restored.sub == payload.sub
        assert restored.jti == payload.jti
        assert restored.token_type == payload.token_type
        assert list(restored.scopes) == list(payload.scopes)


class TestTokenPrettyPrint:
    """Property tests for token pretty printing.
    
    **Feature: core-code-review, Property 23: Token Pretty Print Completeness**
    **Validates: Requirements 12.1**
    """

    @given(
        user_id=st.text(min_size=1, max_size=50, alphabet=string.ascii_letters),
        scopes=st.lists(st.text(min_size=1, max_size=20, alphabet=string.ascii_lowercase), max_size=3),
    )
    @settings(max_examples=50)
    def test_pretty_print_contains_all_fields(self, user_id: str, scopes: list[str]):
        """For any TokenPayload, pretty_print() SHALL include all fields."""
        assume(len(user_id) > 0)
        
        now = datetime.now(timezone.utc)
        payload = TokenPayload(
            sub=user_id,
            exp=now + timedelta(hours=1),
            iat=now,
            jti="test-jti-123",
            scopes=tuple(scopes),
            token_type="access",
        )
        
        output = payload.pretty_print()
        
        # All fields should be present
        assert "sub:" in output
        assert "exp:" in output
        assert "iat:" in output
        assert "jti:" in output
        assert "scopes:" in output
        assert "token_type:" in output
        
        # Values should be present
        assert user_id in output
        assert "test-jti-123" in output


class TestTokenPairSerialization:
    """Property tests for TokenPair serialization."""

    def test_token_pair_to_dict(self):
        """TokenPair.to_dict() SHALL produce valid structure."""
        pair = TokenPair(
            access_token="access.token.here",
            refresh_token="refresh.token.here",
            token_type="bearer",
            expires_in=1800,
        )
        
        result = pair.to_dict()
        
        assert result["access_token"] == "access.token.here"
        assert result["refresh_token"] == "refresh.token.here"
        assert result["token_type"] == "bearer"
        assert result["expires_in"] == 1800
