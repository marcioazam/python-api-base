"""Tests for multitenancy tenant module.

Tests for TenantInfo, TenantContext, TenantSchemaManager, TenantScopedCache.
"""

import pytest

from infrastructure.multitenancy.tenant import (
    SchemaConfig,
    TenantAuditEntry,
    TenantContext,
    TenantInfo,
    TenantResolutionStrategy,
    TenantSchemaManager,
    TenantScopedCache,
)


class TestTenantResolutionStrategy:
    """Tests for TenantResolutionStrategy enum."""

    def test_header_value(self) -> None:
        """HEADER should have correct value."""
        assert TenantResolutionStrategy.HEADER.value == "header"

    def test_subdomain_value(self) -> None:
        """SUBDOMAIN should have correct value."""
        assert TenantResolutionStrategy.SUBDOMAIN.value == "subdomain"

    def test_path_value(self) -> None:
        """PATH should have correct value."""
        assert TenantResolutionStrategy.PATH.value == "path"

    def test_jwt_claim_value(self) -> None:
        """JWT_CLAIM should have correct value."""
        assert TenantResolutionStrategy.JWT_CLAIM.value == "jwt_claim"

    def test_query_param_value(self) -> None:
        """QUERY_PARAM should have correct value."""
        assert TenantResolutionStrategy.QUERY_PARAM.value == "query_param"


class TestTenantInfo:
    """Tests for TenantInfo dataclass."""

    def test_init_with_id_and_name(self) -> None:
        """TenantInfo should store id and name."""
        tenant: TenantInfo[str] = TenantInfo(id="t1", name="Tenant 1")
        assert tenant.id == "t1"
        assert tenant.name == "Tenant 1"

    def test_default_schema_name(self) -> None:
        """TenantInfo should have None schema_name by default."""
        tenant: TenantInfo[str] = TenantInfo(id="t1", name="Test")
        assert tenant.schema_name is None

    def test_custom_schema_name(self) -> None:
        """TenantInfo should store custom schema_name."""
        tenant: TenantInfo[str] = TenantInfo(
            id="t1", name="Test", schema_name="tenant_t1"
        )
        assert tenant.schema_name == "tenant_t1"

    def test_default_settings(self) -> None:
        """TenantInfo should have None settings by default."""
        tenant: TenantInfo[str] = TenantInfo(id="t1", name="Test")
        assert tenant.settings is None

    def test_custom_settings(self) -> None:
        """TenantInfo should store custom settings."""
        settings = {"theme": "dark", "locale": "en"}
        tenant: TenantInfo[str] = TenantInfo(id="t1", name="Test", settings=settings)
        assert tenant.settings == settings

    def test_default_is_active(self) -> None:
        """TenantInfo should be active by default."""
        tenant: TenantInfo[str] = TenantInfo(id="t1", name="Test")
        assert tenant.is_active is True

    def test_inactive_tenant(self) -> None:
        """TenantInfo can be inactive."""
        tenant: TenantInfo[str] = TenantInfo(id="t1", name="Test", is_active=False)
        assert tenant.is_active is False

    def test_is_frozen(self) -> None:
        """TenantInfo should be immutable."""
        tenant: TenantInfo[str] = TenantInfo(id="t1", name="Test")
        with pytest.raises(AttributeError):
            tenant.name = "Changed"  # type: ignore

    def test_int_id_type(self) -> None:
        """TenantInfo should support int ID type."""
        tenant: TenantInfo[int] = TenantInfo(id=123, name="Test")
        assert tenant.id == 123


class TestTenantContext:
    """Tests for TenantContext class."""

    def test_default_strategy(self) -> None:
        """Default strategy should be HEADER."""
        ctx: TenantContext[str] = TenantContext()
        assert ctx._strategy == TenantResolutionStrategy.HEADER

    def test_custom_strategy(self) -> None:
        """Should accept custom strategy."""
        ctx: TenantContext[str] = TenantContext(
            strategy=TenantResolutionStrategy.JWT_CLAIM
        )
        assert ctx._strategy == TenantResolutionStrategy.JWT_CLAIM

    def test_default_header_name(self) -> None:
        """Default header name should be X-Tenant-ID."""
        ctx: TenantContext[str] = TenantContext()
        assert ctx._header_name == "X-Tenant-ID"

    def test_custom_header_name(self) -> None:
        """Should accept custom header name."""
        ctx: TenantContext[str] = TenantContext(header_name="X-Organization")
        assert ctx._header_name == "X-Organization"

    def test_get_current_default_none(self) -> None:
        """get_current should return None by default."""
        TenantContext.set_current(None)
        assert TenantContext.get_current() is None

    def test_set_and_get_current(self) -> None:
        """set_current and get_current should work together."""
        tenant: TenantInfo[str] = TenantInfo(id="t1", name="Test")
        TenantContext.set_current(tenant)
        assert TenantContext.get_current() == tenant
        TenantContext.set_current(None)  # Cleanup

    def test_resolve_from_headers(self) -> None:
        """resolve_from_headers should extract tenant ID."""
        ctx: TenantContext[str] = TenantContext()
        headers = {"X-Tenant-ID": "tenant-123"}
        assert ctx.resolve_from_headers(headers) == "tenant-123"

    def test_resolve_from_headers_missing(self) -> None:
        """resolve_from_headers should return None if missing."""
        ctx: TenantContext[str] = TenantContext()
        headers = {"Other-Header": "value"}
        assert ctx.resolve_from_headers(headers) is None

    def test_resolve_from_jwt(self) -> None:
        """resolve_from_jwt should extract tenant ID from claims."""
        ctx: TenantContext[str] = TenantContext()
        claims = {"tenant_id": "tenant-456", "sub": "user-1"}
        assert ctx.resolve_from_jwt(claims) == "tenant-456"

    def test_resolve_from_jwt_custom_claim(self) -> None:
        """resolve_from_jwt should use custom claim name."""
        ctx: TenantContext[str] = TenantContext(jwt_claim="org_id")
        claims = {"org_id": "org-789"}
        assert ctx.resolve_from_jwt(claims) == "org-789"

    def test_resolve_from_query(self) -> None:
        """resolve_from_query should extract tenant ID."""
        ctx: TenantContext[str] = TenantContext()
        params = {"tenant_id": "tenant-abc"}
        assert ctx.resolve_from_query(params) == "tenant-abc"

    def test_resolve_from_query_custom_param(self) -> None:
        """resolve_from_query should use custom param name."""
        ctx: TenantContext[str] = TenantContext(query_param="org")
        params = {"org": "org-xyz"}
        assert ctx.resolve_from_query(params) == "org-xyz"


class TestSchemaConfig:
    """Tests for SchemaConfig dataclass."""

    def test_default_schema(self) -> None:
        """Default schema should be 'public'."""
        config = SchemaConfig()
        assert config.default_schema == "public"

    def test_default_prefix(self) -> None:
        """Default prefix should be 'tenant_'."""
        config = SchemaConfig()
        assert config.schema_prefix == "tenant_"

    def test_default_create_on_provision(self) -> None:
        """create_on_provision should be True by default."""
        config = SchemaConfig()
        assert config.create_on_provision is True


class TestTenantSchemaManager:
    """Tests for TenantSchemaManager class."""

    def test_get_schema_name(self) -> None:
        """get_schema_name should return prefixed name."""
        config = SchemaConfig()
        manager: TenantSchemaManager[str] = TenantSchemaManager(config)
        assert manager.get_schema_name("abc") == "tenant_abc"

    def test_get_schema_name_custom_prefix(self) -> None:
        """get_schema_name should use custom prefix."""
        config = SchemaConfig(schema_prefix="org_")
        manager: TenantSchemaManager[str] = TenantSchemaManager(config)
        assert manager.get_schema_name("123") == "org_123"

    def test_get_connection_schema_with_schema_name(self) -> None:
        """get_connection_schema should use tenant's schema_name if set."""
        config = SchemaConfig()
        manager: TenantSchemaManager[str] = TenantSchemaManager(config)
        tenant: TenantInfo[str] = TenantInfo(
            id="t1", name="Test", schema_name="custom_schema"
        )
        assert manager.get_connection_schema(tenant) == "custom_schema"

    def test_get_connection_schema_without_schema_name(self) -> None:
        """get_connection_schema should generate name if not set."""
        config = SchemaConfig()
        manager: TenantSchemaManager[str] = TenantSchemaManager(config)
        tenant: TenantInfo[str] = TenantInfo(id="t1", name="Test")
        assert manager.get_connection_schema(tenant) == "tenant_t1"


class TestTenantScopedCache:
    """Tests for TenantScopedCache class."""

    def test_default_prefix(self) -> None:
        """Default prefix should be 'tenant'."""
        cache: TenantScopedCache[str] = TenantScopedCache()
        assert cache._prefix == "tenant"

    def test_custom_prefix(self) -> None:
        """Should accept custom prefix."""
        cache: TenantScopedCache[str] = TenantScopedCache(prefix="org")
        assert cache._prefix == "org"

    def test_get_key(self) -> None:
        """get_key should return scoped key."""
        cache: TenantScopedCache[str] = TenantScopedCache()
        key = cache.get_key("t1", "user:123")
        assert key == "tenant:t1:user:123"

    def test_get_pattern(self) -> None:
        """get_pattern should return wildcard pattern."""
        cache: TenantScopedCache[str] = TenantScopedCache()
        pattern = cache.get_pattern("t1")
        assert pattern == "tenant:t1:*"


class TestTenantAuditEntry:
    """Tests for TenantAuditEntry dataclass."""

    def test_init_required_fields(self) -> None:
        """TenantAuditEntry should store required fields."""
        entry: TenantAuditEntry[str] = TenantAuditEntry(
            tenant_id="t1",
            user_id="u1",
            action="create",
            resource_type="user",
            resource_id="r1",
            timestamp="2024-01-01T00:00:00Z",
        )
        assert entry.tenant_id == "t1"
        assert entry.user_id == "u1"
        assert entry.action == "create"
        assert entry.resource_type == "user"
        assert entry.resource_id == "r1"
        assert entry.timestamp == "2024-01-01T00:00:00Z"

    def test_default_details(self) -> None:
        """TenantAuditEntry should have None details by default."""
        entry: TenantAuditEntry[str] = TenantAuditEntry(
            tenant_id="t1",
            user_id="u1",
            action="read",
            resource_type="doc",
            resource_id="d1",
            timestamp="2024-01-01T00:00:00Z",
        )
        assert entry.details is None

    def test_custom_details(self) -> None:
        """TenantAuditEntry should store custom details."""
        details = {"ip": "192.168.1.1", "browser": "Chrome"}
        entry: TenantAuditEntry[str] = TenantAuditEntry(
            tenant_id="t1",
            user_id="u1",
            action="login",
            resource_type="session",
            resource_id="s1",
            timestamp="2024-01-01T00:00:00Z",
            details=details,
        )
        assert entry.details == details

    def test_is_frozen(self) -> None:
        """TenantAuditEntry should be immutable."""
        entry: TenantAuditEntry[str] = TenantAuditEntry(
            tenant_id="t1",
            user_id="u1",
            action="test",
            resource_type="test",
            resource_id="t1",
            timestamp="2024-01-01T00:00:00Z",
        )
        with pytest.raises(AttributeError):
            entry.action = "changed"  # type: ignore
