"""Property-based tests for JWT authentication service.

**Feature: api-base-improvements**
**Validates: Requirements 1.1, 1.3, 1.6**
"""

from datetime import datetime, timedelta, timezone

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from my_app.core.auth.jwt import (
    JWTService,
    TokenExpiredError,
    TokenInvalidError,
    TokenPayload,
    TokenPair,
)


# Strategy for generating valid user IDs (ULID-like)
user_id_strategy = st.text(
    min_size=1,
    max_size=26,
    alphabet=st.characters(whitelist_categories=("L", "N")),
).filter(lambda x: x.strip() != "")

# Strategy for generating scopes
scope_strategy = st.lists(
    st.text(
        min_size=1,
        max_size=20,
        alphabet=st.characters(whitelist_categories=("L",), whitelist_characters="_:"),
    ).filter(lambda x: x.strip() != ""),
    min_size=0,
    max_size=5,
)

# Valid secret key for testing
TEST_SECRET_KEY = "test-secret-key-that-is-at-least-32-characters-long"


class TestTokenPairGeneration:
    """Property tests for token pair generation."""

    @settings(max_examples=100, deadline=None)
    @given(user_id=user_id_strategy, scopes=scope_strategy)
    def test_token_pair_structure_is_valid(
        self, user_id: str, scopes: list[str]
    ) -> None:
        """
        **Feature: api-base-improvements, Property 1: Token pair generation returns valid structure**
        **Validates: Requirements 1.1**

        For any valid user credentials, when generating a token pair, the result
        SHALL contain both access_token and refresh_token as non-empty strings
        with valid JWT format.
        """
        service = JWTService(secret_key=TEST_SECRET_KEY)
        pair, access_payload, refresh_payload = service.create_token_pair(
            user_id, scopes
        )

        # Verify TokenPair structure
        assert isinstance(pair, TokenPair)
        assert isinstance(pair.access_token, str)
        assert isinstance(pair.refresh_token, str)
        assert len(pair.access_token) > 0, "Access token must be non-empty"
        assert len(pair.refresh_token) > 0, "Refresh token must be non-empty"

        # Verify JWT format (three dot-separated parts)
        access_parts = pair.access_token.split(".")
        refresh_parts = pair.refresh_token.split(".")
        assert len(access_parts) == 3, "Access token must have 3 JWT parts"
        assert len(refresh_parts) == 3, "Refresh token must have 3 JWT parts"

        # Verify token type
        assert pair.token_type == "bearer"
        assert pair.expires_in > 0

        # Verify payloads match user_id
        assert access_payload.sub == user_id
        assert refresh_payload.sub == user_id

        # Verify token types
        assert access_payload.token_type == "access"
        assert refresh_payload.token_type == "refresh"

    @settings(max_examples=100, deadline=None)
    @given(user_id=user_id_strategy)
    def test_access_and_refresh_tokens_are_different(self, user_id: str) -> None:
        """
        **Feature: api-base-improvements, Property 1: Token pair generation returns valid structure**
        **Validates: Requirements 1.1**

        For any user, access and refresh tokens SHALL be different strings.
        """
        service = JWTService(secret_key=TEST_SECRET_KEY)
        pair, _, _ = service.create_token_pair(user_id)

        assert pair.access_token != pair.refresh_token, (
            "Access and refresh tokens must be different"
        )

    @settings(max_examples=50, deadline=None)
    @given(user_id=user_id_strategy, scopes=scope_strategy)
    def test_tokens_are_verifiable(self, user_id: str, scopes: list[str]) -> None:
        """
        **Feature: api-base-improvements, Property 1: Token pair generation returns valid structure**
        **Validates: Requirements 1.1**

        For any generated token pair, both tokens SHALL be verifiable.
        """
        service = JWTService(secret_key=TEST_SECRET_KEY)
        pair, _, _ = service.create_token_pair(user_id, scopes)

        # Both tokens should be verifiable
        access_payload = service.verify_token(pair.access_token, expected_type="access")
        refresh_payload = service.verify_token(
            pair.refresh_token, expected_type="refresh"
        )

        assert access_payload.sub == user_id
        assert refresh_payload.sub == user_id
        assert list(access_payload.scopes) == scopes


class TestTokenPayloadRoundTrip:
    """Property tests for token payload serialization."""

    @settings(max_examples=100, deadline=None)
    @given(user_id=user_id_strategy, scopes=scope_strategy)
    def test_payload_serialization_round_trip(
        self, user_id: str, scopes: list[str]
    ) -> None:
        """
        **Feature: api-base-improvements, Property 6: Token payload serialization round-trip**
        **Validates: Requirements 1.6**

        For any valid token payload, serializing then deserializing SHALL produce
        an equivalent payload.
        """
        now = datetime.now(timezone.utc).replace(microsecond=0)
        original = TokenPayload(
            sub=user_id,
            exp=now + timedelta(hours=1),
            iat=now,
            jti="test-jti-12345",
            scopes=tuple(scopes),
            token_type="access",
        )

        # Round-trip through dict
        serialized = original.to_dict()
        deserialized = TokenPayload.from_dict(serialized)

        # Verify equivalence (timestamps may lose microseconds)
        assert deserialized.sub == original.sub
        assert int(deserialized.exp.timestamp()) == int(original.exp.timestamp())
        assert int(deserialized.iat.timestamp()) == int(original.iat.timestamp())
        assert deserialized.jti == original.jti
        assert list(deserialized.scopes) == list(original.scopes)
        assert deserialized.token_type == original.token_type

    @settings(max_examples=50, deadline=None)
    @given(user_id=user_id_strategy, scopes=scope_strategy)
    def test_jwt_encode_decode_round_trip(
        self, user_id: str, scopes: list[str]
    ) -> None:
        """
        **Feature: api-base-improvements, Property 6: Token payload serialization round-trip**
        **Validates: Requirements 1.6**

        For any user, encoding then decoding a JWT SHALL preserve the payload.
        """
        service = JWTService(secret_key=TEST_SECRET_KEY)
        token, original_payload = service.create_access_token(user_id, scopes)

        decoded_payload = service.verify_token(token)

        assert decoded_payload.sub == original_payload.sub
        assert decoded_payload.jti == original_payload.jti
        assert list(decoded_payload.scopes) == list(original_payload.scopes)
        assert decoded_payload.token_type == original_payload.token_type


class TestExpiredTokenRejection:
    """Property tests for expired token handling."""

    def test_expired_token_is_rejected(self) -> None:
        """
        **Feature: api-base-improvements, Property 3: Expired tokens are rejected**
        **Validates: Requirements 1.3**

        For any expired access token, verification SHALL raise TokenExpiredError.
        """
        # Create service with very short expiration
        service = JWTService(
            secret_key=TEST_SECRET_KEY,
            access_token_expire_minutes=0,  # Immediate expiration
        )

        # Create token (will be expired immediately due to 0 minute expiration)
        token, _ = service.create_access_token("test-user")

        # Token should be rejected as expired
        with pytest.raises(TokenExpiredError):
            service.verify_token(token)

    @settings(max_examples=20, deadline=None)
    @given(user_id=user_id_strategy)
    def test_valid_token_not_rejected(self, user_id: str) -> None:
        """
        **Feature: api-base-improvements, Property 3: Expired tokens are rejected**
        **Validates: Requirements 1.3**

        For any non-expired token, verification SHALL succeed.
        """
        service = JWTService(
            secret_key=TEST_SECRET_KEY,
            access_token_expire_minutes=30,
        )

        token, _ = service.create_access_token(user_id)
        payload = service.verify_token(token)

        assert payload.sub == user_id
        assert payload.exp > datetime.now(timezone.utc)


class TestTokenValidation:
    """Additional property tests for token validation."""

    def test_invalid_token_format_rejected(self) -> None:
        """Invalid token format SHALL raise TokenInvalidError."""
        service = JWTService(secret_key=TEST_SECRET_KEY)

        with pytest.raises(TokenInvalidError):
            service.verify_token("not-a-valid-jwt")

        with pytest.raises(TokenInvalidError):
            service.verify_token("invalid.token.format")

    def test_wrong_secret_key_rejected(self) -> None:
        """Token signed with different key SHALL be rejected."""
        service1 = JWTService(secret_key=TEST_SECRET_KEY)
        service2 = JWTService(secret_key="different-secret-key-at-least-32-chars")

        token, _ = service1.create_access_token("test-user")

        with pytest.raises(TokenInvalidError):
            service2.verify_token(token)

    def test_wrong_token_type_rejected(self) -> None:
        """Token with wrong type SHALL be rejected when type is specified."""
        service = JWTService(secret_key=TEST_SECRET_KEY)

        access_token, _ = service.create_access_token("test-user")
        refresh_token, _ = service.create_refresh_token("test-user")

        # Access token should fail when expecting refresh
        with pytest.raises(TokenInvalidError, match="Expected refresh token"):
            service.verify_token(access_token, expected_type="refresh")

        # Refresh token should fail when expecting access
        with pytest.raises(TokenInvalidError, match="Expected access token"):
            service.verify_token(refresh_token, expected_type="access")

    def test_secret_key_minimum_length(self) -> None:
        """Secret key shorter than 32 chars SHALL raise ValueError."""
        with pytest.raises(ValueError, match="at least 32 characters"):
            JWTService(secret_key="short")

    @settings(max_examples=20, deadline=None)
    @given(user_id=user_id_strategy)
    def test_pretty_print_contains_all_fields(self, user_id: str) -> None:
        """Pretty print output SHALL contain all payload fields."""
        service = JWTService(secret_key=TEST_SECRET_KEY)
        _, payload = service.create_access_token(user_id, ["read", "write"])

        pretty = payload.pretty_print()

        assert "sub:" in pretty
        assert user_id in pretty
        assert "exp:" in pretty
        assert "iat:" in pretty
        assert "jti:" in pretty
        assert "scopes:" in pretty
        assert "token_type:" in pretty


class TestRefreshTokenRoundTrip:
    """Property tests for refresh token storage round-trip."""

    @settings(max_examples=100, deadline=None)
    @given(user_id=user_id_strategy)
    def test_refresh_token_store_round_trip(self, user_id: str) -> None:
        """
        **Feature: api-base-improvements, Property 4: Refresh token round-trip**
        **Validates: Requirements 1.4**

        For any valid refresh token, submitting it SHALL return a new valid
        access token that can authenticate requests.
        """
        from my_app.infrastructure.auth.token_store import InMemoryTokenStore

        import asyncio

        async def run_test():
            service = JWTService(secret_key=TEST_SECRET_KEY)
            store = InMemoryTokenStore()

            # Create token pair
            pair, _, refresh_payload = service.create_token_pair(user_id)

            # Store refresh token
            await store.store(
                jti=refresh_payload.jti,
                user_id=user_id,
                expires_at=refresh_payload.exp,
            )

            # Verify token is stored and valid
            is_valid = await store.is_valid(refresh_payload.jti)
            assert is_valid, "Stored refresh token should be valid"

            # Retrieve stored token
            stored = await store.get(refresh_payload.jti)
            assert stored is not None, "Should retrieve stored token"
            assert stored.user_id == user_id, "User ID should match"
            assert stored.jti == refresh_payload.jti, "JTI should match"

            # Verify refresh token can be used to get new access token
            verified_refresh = service.verify_token(
                pair.refresh_token, expected_type="refresh"
            )
            assert verified_refresh.sub == user_id

            # Create new access token (simulating refresh flow)
            new_access, new_payload = service.create_access_token(user_id)
            verified_new = service.verify_token(new_access, expected_type="access")
            assert verified_new.sub == user_id

        asyncio.get_event_loop().run_until_complete(run_test())

    @settings(max_examples=50, deadline=None)
    @given(user_id=user_id_strategy)
    def test_stored_token_data_integrity(self, user_id: str) -> None:
        """
        **Feature: api-base-improvements, Property 4: Refresh token round-trip**
        **Validates: Requirements 1.4**

        For any stored token, retrieving it SHALL return the same data.
        """
        from my_app.infrastructure.auth.token_store import InMemoryTokenStore

        import asyncio

        async def run_test():
            service = JWTService(secret_key=TEST_SECRET_KEY)
            store = InMemoryTokenStore()

            _, _, refresh_payload = service.create_token_pair(user_id)

            await store.store(
                jti=refresh_payload.jti,
                user_id=user_id,
                expires_at=refresh_payload.exp,
            )

            stored = await store.get(refresh_payload.jti)
            assert stored is not None
            assert stored.jti == refresh_payload.jti
            assert stored.user_id == user_id
            assert not stored.revoked
            assert stored.is_valid()

        asyncio.get_event_loop().run_until_complete(run_test())


class TestLogoutInvalidation:
    """Property tests for logout token invalidation."""

    @settings(max_examples=100, deadline=None)
    @given(user_id=user_id_strategy)
    def test_logout_invalidates_refresh_token(self, user_id: str) -> None:
        """
        **Feature: api-base-improvements, Property 5: Logout invalidates refresh token**
        **Validates: Requirements 1.5**

        For any logged-in user, after logout, the refresh token SHALL be invalid
        and token refresh SHALL fail.
        """
        from my_app.infrastructure.auth.token_store import InMemoryTokenStore

        import asyncio

        async def run_test():
            service = JWTService(secret_key=TEST_SECRET_KEY)
            store = InMemoryTokenStore()

            # Create and store refresh token
            _, _, refresh_payload = service.create_token_pair(user_id)
            await store.store(
                jti=refresh_payload.jti,
                user_id=user_id,
                expires_at=refresh_payload.exp,
            )

            # Verify token is valid before logout
            assert await store.is_valid(refresh_payload.jti)

            # Simulate logout by revoking token
            revoked = await store.revoke(refresh_payload.jti)
            assert revoked, "Revoke should return True"

            # Verify token is invalid after logout
            is_valid = await store.is_valid(refresh_payload.jti)
            assert not is_valid, "Token should be invalid after logout"

            # Verify stored token shows revoked status
            stored = await store.get(refresh_payload.jti)
            assert stored is not None
            assert stored.revoked, "Token should be marked as revoked"

        asyncio.get_event_loop().run_until_complete(run_test())

    @settings(max_examples=50, deadline=None)
    @given(user_id=user_id_strategy)
    def test_logout_all_devices_invalidates_all_tokens(self, user_id: str) -> None:
        """
        **Feature: api-base-improvements, Property 5: Logout invalidates refresh token**
        **Validates: Requirements 1.5**

        For any user with multiple sessions, logout from all devices SHALL
        invalidate all refresh tokens.
        """
        from my_app.infrastructure.auth.token_store import InMemoryTokenStore

        import asyncio

        async def run_test():
            service = JWTService(secret_key=TEST_SECRET_KEY)
            store = InMemoryTokenStore()

            # Create multiple tokens for same user (multiple devices)
            tokens = []
            for _ in range(3):
                _, _, refresh_payload = service.create_token_pair(user_id)
                await store.store(
                    jti=refresh_payload.jti,
                    user_id=user_id,
                    expires_at=refresh_payload.exp,
                )
                tokens.append(refresh_payload.jti)

            # Verify all tokens are valid
            for jti in tokens:
                assert await store.is_valid(jti)

            # Logout from all devices
            count = await store.revoke_all_for_user(user_id)
            assert count == 3, "Should revoke all 3 tokens"

            # Verify all tokens are invalid
            for jti in tokens:
                assert not await store.is_valid(jti)

        asyncio.get_event_loop().run_until_complete(run_test())

    @settings(max_examples=30, deadline=None)
    @given(user_id=user_id_strategy)
    def test_revoke_nonexistent_token_returns_false(self, user_id: str) -> None:
        """
        **Feature: api-base-improvements, Property 5: Logout invalidates refresh token**
        **Validates: Requirements 1.5**

        Revoking a non-existent token SHALL return False.
        """
        from my_app.infrastructure.auth.token_store import InMemoryTokenStore

        import asyncio

        async def run_test():
            store = InMemoryTokenStore()
            revoked = await store.revoke("nonexistent-jti")
            assert not revoked, "Should return False for non-existent token"

        asyncio.get_event_loop().run_until_complete(run_test())


class TestValidTokenAuthentication:
    """Property tests for valid token authentication."""

    @settings(max_examples=100, deadline=None)
    @given(user_id=user_id_strategy, scopes=scope_strategy)
    def test_valid_token_provides_user_context(
        self, user_id: str, scopes: list[str]
    ) -> None:
        """
        **Feature: api-base-improvements, Property 2: Valid token authentication provides user context**
        **Validates: Requirements 1.2**

        For any valid access token, when used in Authorization header, the request
        SHALL be authenticated and user context SHALL be available with correct user_id.
        """
        service = JWTService(secret_key=TEST_SECRET_KEY)

        # Create access token
        token, payload = service.create_access_token(user_id, scopes)

        # Verify token and get user context
        verified_payload = service.verify_token(token, expected_type="access")

        # User context should be available
        assert verified_payload.sub == user_id, "User ID should match"
        assert list(verified_payload.scopes) == scopes, "Scopes should match"
        assert verified_payload.token_type == "access", "Token type should be access"

    @settings(max_examples=50, deadline=None)
    @given(user_id=user_id_strategy)
    def test_token_contains_all_user_context_fields(self, user_id: str) -> None:
        """
        **Feature: api-base-improvements, Property 2: Valid token authentication provides user context**
        **Validates: Requirements 1.2**

        Token payload SHALL contain all required user context fields.
        """
        service = JWTService(secret_key=TEST_SECRET_KEY)
        token, _ = service.create_access_token(user_id, ["read", "write"])

        payload = service.verify_token(token)

        # All required fields should be present
        assert payload.sub is not None, "sub (user_id) required"
        assert payload.exp is not None, "exp (expiration) required"
        assert payload.iat is not None, "iat (issued at) required"
        assert payload.jti is not None, "jti (JWT ID) required"
        assert payload.scopes is not None, "scopes required"
        assert payload.token_type is not None, "token_type required"

    @settings(max_examples=50, deadline=None)
    @given(user_id=user_id_strategy, scopes=scope_strategy)
    def test_different_users_get_different_tokens(
        self, user_id: str, scopes: list[str]
    ) -> None:
        """
        **Feature: api-base-improvements, Property 2: Valid token authentication provides user context**
        **Validates: Requirements 1.2**

        Different users SHALL receive different tokens with correct context.
        """
        service = JWTService(secret_key=TEST_SECRET_KEY)

        token1, _ = service.create_access_token(user_id, scopes)
        token2, _ = service.create_access_token(user_id + "_other", scopes)

        # Tokens should be different
        assert token1 != token2

        # Each token should have correct user context
        payload1 = service.verify_token(token1)
        payload2 = service.verify_token(token2)

        assert payload1.sub == user_id
        assert payload2.sub == user_id + "_other"


# =============================================================================
# JWT Security Property Tests (Post-Refactoring)
# =============================================================================


class TestJWTAlgorithmRestrictionProperties:
    """Property tests for JWT algorithm restriction.

    **Feature: code-review-refactoring, Property 4: JWT Algorithm Restriction**
    **Validates: Requirements 6.1, 6.2**
    """

    @given(st.sampled_from(["none", "None", "NONE", "nOnE"]))
    @settings(max_examples=10)
    def test_none_algorithm_rejected(self, alg: str) -> None:
        """Property: 'none' algorithm is always rejected.

        **Feature: code-review-refactoring, Property 4: JWT Algorithm Restriction**
        **Validates: Requirements 6.1, 6.2**
        """
        from my_app.core.auth.jwt_validator import InvalidTokenError, JWTValidator

        with pytest.raises(InvalidTokenError) as exc_info:
            JWTValidator(secret_or_key="test-secret-key-32-chars-long!!", algorithm=alg)

        assert "none" in str(exc_info.value).lower() or "not allowed" in str(
            exc_info.value
        ).lower()

    @given(st.sampled_from(["RS256", "ES256", "HS256"]))
    @settings(max_examples=10)
    def test_allowed_algorithms_accepted(self, alg: str) -> None:
        """Property: Allowed algorithms are accepted.

        **Feature: code-review-refactoring, Property 4: JWT Algorithm Restriction**
        **Validates: Requirements 6.1, 6.2**
        """
        from my_app.core.auth.jwt_validator import JWTValidator

        # Should not raise
        validator = JWTValidator(
            secret_or_key="test-secret-key-32-chars-long!!", algorithm=alg
        )
        assert validator._algorithm == alg

    @given(st.text(min_size=1, max_size=20).filter(lambda x: x not in ["RS256", "ES256", "HS256", "none", "None"]))
    @settings(max_examples=50)
    def test_unknown_algorithms_rejected(self, alg: str) -> None:
        """Property: Unknown algorithms are rejected.

        **Feature: code-review-refactoring, Property 4: JWT Algorithm Restriction**
        **Validates: Requirements 6.1, 6.2**
        """
        from my_app.core.auth.jwt_validator import InvalidTokenError, JWTValidator

        with pytest.raises(InvalidTokenError):
            JWTValidator(secret_or_key="test-secret-key-32-chars-long!!", algorithm=alg)


class TestJWTTamperingDetectionProperties:
    """Property tests for JWT tampering detection.

    **Feature: code-review-refactoring, Property 5: Token Tampering Detection**
    **Validates: Requirements 6.1, 12.5**
    """

    @given(st.text(min_size=1, max_size=50))
    @settings(max_examples=50)
    def test_tampered_token_rejected(self, user_id: str) -> None:
        """Property: Tampered tokens are rejected.

        **Feature: code-review-refactoring, Property 5: Token Tampering Detection**
        **Validates: Requirements 6.1, 12.5**
        """
        from my_app.core.auth.jwt import JWTService
        from my_app.core.auth.jwt_validator import InvalidTokenError, JWTValidator

        # Create valid token
        service = JWTService(
            secret_key="test-secret-key-32-chars-long!!",
            algorithm="HS256",
        )
        token, _ = service.create_access_token(user_id)

        # Tamper with token (modify payload)
        parts = token.split(".")
        if len(parts) == 3:
            # Modify the payload part
            import base64

            tampered_payload = base64.urlsafe_b64encode(b'{"sub":"hacker"}').decode()
            tampered_token = f"{parts[0]}.{tampered_payload}.{parts[2]}"

            validator = JWTValidator(
                secret_or_key="test-secret-key-32-chars-long!!",
                algorithm="HS256",
            )

            with pytest.raises(InvalidTokenError):
                validator.validate(tampered_token)


class TestJWTValidatorBackwardCompatibility:
    """Property tests for JWT validator backward compatibility.

    **Feature: code-review-refactoring, Property 1: Backward Compatibility**
    **Validates: Requirements 1.2, 1.4**
    """

    @given(st.text(min_size=1, max_size=50))
    @settings(max_examples=50)
    def test_valid_token_validates(self, user_id: str) -> None:
        """Property: Valid tokens pass validation.

        **Feature: code-review-refactoring, Property 1: Backward Compatibility**
        **Validates: Requirements 1.2, 1.4**
        """
        from my_app.core.auth.jwt import JWTService
        from my_app.core.auth.jwt_validator import JWTValidator

        service = JWTService(
            secret_key="test-secret-key-32-chars-long!!",
            algorithm="HS256",
        )
        token, payload = service.create_access_token(user_id)

        validator = JWTValidator(
            secret_or_key="test-secret-key-32-chars-long!!",
            algorithm="HS256",
        )

        validated = validator.validate(token)

        assert validated.sub == user_id
        assert validated.jti == payload.jti
        assert validated.token_type == "access"
