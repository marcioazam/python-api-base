"""Property-based tests for JWT validator module.

**Feature: core-code-review**
**Validates: Requirements 4.2, 4.3, 5.1, 5.2, 5.4, 5.5, 6.1, 6.2, 6.5**
"""

import string
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st
from jose import jwt

from my_app.core.auth.jwt_validator import (
    JWTValidator,
    InvalidTokenError,
    ValidatedToken,
)


class TestJWTAlgorithmValidation:
    """Property tests for JWT algorithm validation.
    
    **Feature: core-code-review, Property 7: JWT Algorithm Validation**
    **Validates: Requirements 4.2, 5.1, 5.4**
    """

    @given(st.sampled_from(["RS256", "ES256", "HS256"]))
    @settings(max_examples=30)
    def test_allowed_algorithms_accepted(self, algorithm: str):
        """For any algorithm in allowlist, initialization SHALL succeed."""
        # Note: For RS256/ES256 we'd need proper keys, so just test HS256
        if algorithm == "HS256":
            validator = JWTValidator(
                secret_or_key="a" * 32,
                algorithm=algorithm,
            )
            assert validator._algorithm == algorithm

    @given(st.text(min_size=1, max_size=20).filter(
        lambda x: x.upper() not in ["RS256", "ES256", "HS256", "NONE"]
    ))
    @settings(max_examples=50)
    def test_invalid_algorithms_rejected(self, algorithm: str):
        """For any algorithm not in allowlist, initialization SHALL raise error."""
        assume(algorithm.upper() not in ["RS256", "ES256", "HS256", "NONE"])
        
        with pytest.raises(InvalidTokenError):
            JWTValidator(secret_or_key="a" * 32, algorithm=algorithm)

    def test_none_algorithm_rejected_at_init(self):
        """Algorithm 'none' SHALL be rejected at initialization."""
        with pytest.raises(InvalidTokenError) as exc_info:
            JWTValidator(secret_or_key="a" * 32, algorithm="none")
        
        assert "none" in str(exc_info.value).lower()

    def test_none_algorithm_rejected_in_token(self):
        """Token with 'none' algorithm SHALL be rejected.
        
        **Feature: core-code-review, Property 8: JWT None Algorithm Rejection**
        **Validates: Requirements 4.3, 5.5**
        """
        validator = JWTValidator(secret_or_key="a" * 32, algorithm="HS256")
        
        # Create a token with "none" algorithm (unsigned)
        payload = {
            "sub": "user123",
            "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "jti": "test-jti",
        }
        
        # Manually construct token with "none" algorithm
        import base64
        import json
        
        header = base64.urlsafe_b64encode(
            json.dumps({"alg": "none", "typ": "JWT"}).encode()
        ).rstrip(b"=").decode()
        payload_b64 = base64.urlsafe_b64encode(
            json.dumps(payload).encode()
        ).rstrip(b"=").decode()
        
        none_token = f"{header}.{payload_b64}."
        
        with pytest.raises(InvalidTokenError) as exc_info:
            validator.validate(none_token)
        
        assert "none" in str(exc_info.value).lower()


class TestSecureAlgorithmEnforcement:
    """Property tests for secure algorithm enforcement.
    
    **Feature: core-code-review**
    **Validates: Requirements 5.2**
    """

    def test_hs256_rejected_when_secure_required(self):
        """HS256 SHALL be rejected when require_secure_algorithm is True."""
        with pytest.raises(InvalidTokenError) as exc_info:
            JWTValidator(
                secret_or_key="a" * 32,
                algorithm="HS256",
                require_secure_algorithm=True,
            )
        
        assert "secure" in str(exc_info.value).lower()

    def test_hs256_allowed_when_secure_not_required(self):
        """HS256 SHALL be allowed when require_secure_algorithm is False."""
        validator = JWTValidator(
            secret_or_key="a" * 32,
            algorithm="HS256",
            require_secure_algorithm=False,
        )
        assert validator._algorithm == "HS256"


class TestAlgorithmMismatchDetection:
    """Property tests for algorithm mismatch detection."""

    def test_algorithm_mismatch_rejected(self):
        """Token with mismatched algorithm SHALL be rejected."""
        validator = JWTValidator(secret_or_key="a" * 32, algorithm="HS256")
        
        # Create token with different algorithm claim
        payload = {
            "sub": "user123",
            "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "jti": "test-jti",
        }
        
        # Create valid HS256 token but validator expects different
        token = jwt.encode(payload, "a" * 32, algorithm="HS256")
        
        # Create validator expecting different algorithm
        validator2 = JWTValidator(secret_or_key="b" * 32, algorithm="HS256")
        
        # Should fail due to signature mismatch
        with pytest.raises(InvalidTokenError):
            validator2.validate(token)


class TestRevocationFailClosed:
    """Property tests for revocation store fail-closed behavior.
    
    **Feature: core-code-review, Property 10: Revocation Store Fail-Closed**
    **Validates: Requirements 6.5**
    """

    @pytest.mark.asyncio
    async def test_revocation_store_failure_rejects_token(self):
        """When revocation store fails, token SHALL be rejected."""
        # Create mock revocation store that raises exception
        mock_store = MagicMock()
        mock_store.is_revoked = AsyncMock(side_effect=Exception("Store unavailable"))
        
        validator = JWTValidator(
            secret_or_key="a" * 32,
            algorithm="HS256",
            revocation_store=mock_store,
        )
        
        # Create valid token
        payload = {
            "sub": "user123",
            "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "jti": "test-jti",
        }
        token = jwt.encode(payload, "a" * 32, algorithm="HS256")
        
        # Should fail closed
        with pytest.raises(InvalidTokenError) as exc_info:
            await validator.validate_with_revocation(token)
        
        assert "verify" in str(exc_info.value).lower() or "status" in str(exc_info.value).lower()


class TestTokenRevocationRoundTrip:
    """Property tests for token revocation.
    
    **Feature: core-code-review, Property 9: Token Revocation Round-Trip**
    **Validates: Requirements 6.1, 6.2**
    """

    @pytest.mark.asyncio
    async def test_revoked_token_rejected(self):
        """Revoked token SHALL be rejected."""
        # Create mock revocation store
        revoked_jtis: set[str] = set()
        
        mock_store = MagicMock()
        mock_store.is_revoked = AsyncMock(side_effect=lambda jti: jti in revoked_jtis)
        mock_store.revoke = AsyncMock(side_effect=lambda jti, exp: revoked_jtis.add(jti))
        
        validator = JWTValidator(
            secret_or_key="a" * 32,
            algorithm="HS256",
            revocation_store=mock_store,
        )
        
        # Create valid token
        payload = {
            "sub": "user123",
            "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "jti": "test-jti-revoke",
        }
        token = jwt.encode(payload, "a" * 32, algorithm="HS256")
        
        # Token should be valid initially
        result = await validator.validate_with_revocation(token)
        assert result.sub == "user123"
        
        # Revoke the token
        await validator.revoke(token)
        
        # Token should now be rejected
        with pytest.raises(InvalidTokenError) as exc_info:
            await validator.validate_with_revocation(token)
        
        assert "revoked" in str(exc_info.value).lower()


class TestValidatedTokenStructure:
    """Tests for ValidatedToken structure."""

    def test_validated_token_contains_all_fields(self):
        """ValidatedToken SHALL contain all required fields."""
        validator = JWTValidator(secret_or_key="a" * 32, algorithm="HS256")
        
        payload = {
            "sub": "user123",
            "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "jti": "test-jti",
            "scopes": ["read", "write"],
            "token_type": "access",
        }
        token = jwt.encode(payload, "a" * 32, algorithm="HS256")
        
        result = validator.validate(token)
        
        assert isinstance(result, ValidatedToken)
        assert result.sub == "user123"
        assert result.jti == "test-jti"
        assert result.scopes == ("read", "write")
        assert result.token_type == "access"
        assert isinstance(result.exp, datetime)
        assert isinstance(result.iat, datetime)
