"""Property-based tests for API Key Management.

**Feature: api-architecture-analysis, Priority 11.3: API Key Management**
**Validates: Requirements 5.1, 5.4**
"""

from datetime import datetime, timedelta, UTC

from hypothesis import given, settings
from hypothesis import strategies as st

from my_app.infrastructure.security.api_key_service import (
    APIKey,
    APIKeyService,
    KeyScope,
    KeyStatus,
    create_api_key_service,
)


class TestAPIKeyProperties:
    """Property tests for APIKey."""

    def test_key_is_active_when_status_active_and_not_expired(self) -> None:
        """Key SHALL be active when status is ACTIVE and not expired."""
        key = APIKey(
            key_id="test",
            key_hash="hash",
            client_id="client",
            name="Test Key",
            status=KeyStatus.ACTIVE,
            expires_at=datetime.now(UTC) + timedelta(days=30),
        )

        assert key.is_active is True

    def test_key_is_not_active_when_revoked(self) -> None:
        """Key SHALL not be active when revoked."""
        key = APIKey(
            key_id="test",
            key_hash="hash",
            client_id="client",
            name="Test Key",
            status=KeyStatus.REVOKED,
        )

        assert key.is_active is False

    def test_key_is_not_active_when_expired(self) -> None:
        """Key SHALL not be active when expired."""
        key = APIKey(
            key_id="test",
            key_hash="hash",
            client_id="client",
            name="Test Key",
            status=KeyStatus.ACTIVE,
            expires_at=datetime.now(UTC) - timedelta(days=1),
        )

        assert key.is_active is False
        assert key.is_expired is True

    def test_key_without_expiry_never_expires(self) -> None:
        """Key without expiry SHALL never expire."""
        key = APIKey(
            key_id="test",
            key_hash="hash",
            client_id="client",
            name="Test Key",
            expires_at=None,
        )

        assert key.is_expired is False

    def test_full_scope_grants_all_permissions(self) -> None:
        """FULL scope SHALL grant all permissions."""
        key = APIKey(
            key_id="test",
            key_hash="hash",
            client_id="client",
            name="Test Key",
            scopes=[KeyScope.FULL],
        )

        assert key.has_scope(KeyScope.READ) is True
        assert key.has_scope(KeyScope.WRITE) is True
        assert key.has_scope(KeyScope.ADMIN) is True

    def test_admin_scope_grants_read_write(self) -> None:
        """ADMIN scope SHALL grant READ and WRITE."""
        key = APIKey(
            key_id="test",
            key_hash="hash",
            client_id="client",
            name="Test Key",
            scopes=[KeyScope.ADMIN],
        )

        assert key.has_scope(KeyScope.READ) is True
        assert key.has_scope(KeyScope.WRITE) is True

    def test_read_scope_only_grants_read(self) -> None:
        """READ scope SHALL only grant READ."""
        key = APIKey(
            key_id="test",
            key_hash="hash",
            client_id="client",
            name="Test Key",
            scopes=[KeyScope.READ],
        )

        assert key.has_scope(KeyScope.READ) is True
        assert key.has_scope(KeyScope.WRITE) is False


class TestAPIKeyServiceProperties:
    """Property tests for APIKeyService."""

    def test_create_key_returns_raw_key_and_object(self) -> None:
        """create_key SHALL return raw key and APIKey object."""
        service = APIKeyService()

        raw_key, api_key = service.create_key(
            client_id="client-1",
            name="Test Key",
        )

        assert raw_key.startswith("ak_")
        assert api_key.client_id == "client-1"
        assert api_key.name == "Test Key"
        assert api_key.status == KeyStatus.ACTIVE

    def test_created_key_can_be_validated(self) -> None:
        """Created key SHALL be validated successfully."""
        service = APIKeyService()

        raw_key, api_key = service.create_key(
            client_id="client-1",
            name="Test Key",
        )

        result = service.validate_key(raw_key)

        assert result.valid is True
        assert result.key is not None
        assert result.key.key_id == api_key.key_id

    def test_invalid_key_fails_validation(self) -> None:
        """Invalid key SHALL fail validation."""
        service = APIKeyService()

        result = service.validate_key("invalid_key_12345")

        assert result.valid is False
        assert result.error == "Invalid API key"

    def test_revoked_key_fails_validation(self) -> None:
        """Revoked key SHALL fail validation."""
        service = APIKeyService()

        raw_key, api_key = service.create_key(
            client_id="client-1",
            name="Test Key",
        )

        service.revoke_key(api_key.key_id)
        result = service.validate_key(raw_key)

        assert result.valid is False
        assert "revoked" in result.error.lower()

    def test_scope_validation(self) -> None:
        """Key SHALL fail validation for missing scope."""
        service = APIKeyService()

        raw_key, _ = service.create_key(
            client_id="client-1",
            name="Test Key",
            scopes=[KeyScope.READ],
        )

        result = service.validate_key(raw_key, required_scope=KeyScope.WRITE)

        assert result.valid is False
        assert "scope" in result.error.lower()

    def test_key_rotation_creates_new_key(self) -> None:
        """rotate_key SHALL create new key and mark old as rotated."""
        service = APIKeyService()

        _, old_key = service.create_key(
            client_id="client-1",
            name="Test Key",
        )

        result = service.rotate_key(old_key.key_id)

        assert result.success is True
        assert result.new_key is not None
        assert result.new_key_id is not None
        assert old_key.status == KeyStatus.ROTATED

    def test_rotated_key_fails_validation(self) -> None:
        """Rotated key SHALL fail validation."""
        service = APIKeyService()

        raw_key, old_key = service.create_key(
            client_id="client-1",
            name="Test Key",
        )

        service.rotate_key(old_key.key_id)
        result = service.validate_key(raw_key)

        assert result.valid is False
        assert "rotated" in result.error.lower()

    def test_get_keys_for_client(self) -> None:
        """get_keys_for_client SHALL return all client keys."""
        service = APIKeyService()

        service.create_key(client_id="client-1", name="Key 1")
        service.create_key(client_id="client-1", name="Key 2")
        service.create_key(client_id="client-2", name="Key 3")

        keys = service.get_keys_for_client("client-1")

        assert len(keys) == 2
        assert all(k.client_id == "client-1" for k in keys)

    def test_update_key_scopes(self) -> None:
        """update_key_scopes SHALL update scopes."""
        service = APIKeyService()

        _, api_key = service.create_key(
            client_id="client-1",
            name="Test Key",
            scopes=[KeyScope.READ],
        )

        result = service.update_key_scopes(api_key.key_id, [KeyScope.ADMIN])

        assert result is True
        assert KeyScope.ADMIN in api_key.scopes

    def test_update_key_rate_limit(self) -> None:
        """update_key_rate_limit SHALL update rate limit."""
        service = APIKeyService()

        _, api_key = service.create_key(
            client_id="client-1",
            name="Test Key",
        )

        result = service.update_key_rate_limit(api_key.key_id, 5000)

        assert result is True
        assert api_key.rate_limit == 5000

    def test_extend_key_expiry(self) -> None:
        """extend_key_expiry SHALL extend expiry date."""
        service = APIKeyService()

        _, api_key = service.create_key(
            client_id="client-1",
            name="Test Key",
        )

        original_expiry = api_key.expires_at
        result = service.extend_key_expiry(api_key.key_id, 30)

        assert result is True
        assert api_key.expires_at > original_expiry

    @settings(max_examples=10, deadline=5000)
    @given(num_requests=st.integers(min_value=1, max_value=5))
    def test_rate_limit_tracking(self, num_requests: int) -> None:
        """Service SHALL track rate limit usage."""
        service = APIKeyService()

        raw_key, api_key = service.create_key(
            client_id="client-1",
            name="Test Key",
            rate_limit=100,
        )

        for _ in range(num_requests):
            service.validate_key(raw_key)

        stats = service.get_usage_stats(api_key.key_id)

        assert stats["requests_last_hour"] == num_requests
        assert stats["remaining_requests"] == 100 - num_requests

    def test_rate_limit_exceeded(self) -> None:
        """Validation SHALL fail when rate limit exceeded."""
        service = APIKeyService()

        raw_key, _ = service.create_key(
            client_id="client-1",
            name="Test Key",
            rate_limit=3,
        )

        # Use up rate limit
        for _ in range(3):
            service.validate_key(raw_key)

        # Next request should fail
        result = service.validate_key(raw_key)

        assert result.valid is False
        assert "rate limit" in result.error.lower()

    def test_get_stats(self) -> None:
        """get_stats SHALL return service statistics."""
        service = APIKeyService()

        _, key1 = service.create_key(client_id="c1", name="Key 1")
        service.create_key(client_id="c2", name="Key 2")
        service.revoke_key(key1.key_id)

        stats = service.get_stats()

        assert stats["total_keys"] == 2
        assert stats["active_keys"] == 1
        assert stats["revoked_keys"] == 1


class TestFactoryFunction:
    """Property tests for factory function."""

    def test_create_api_key_service(self) -> None:
        """create_api_key_service SHALL create configured service."""
        service = create_api_key_service(
            key_prefix="custom_",
            default_expiry_days=30,
        )

        raw_key, _ = service.create_key(client_id="c1", name="Test")

        assert raw_key.startswith("custom_")
